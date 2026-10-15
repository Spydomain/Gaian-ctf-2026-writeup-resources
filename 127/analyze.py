#!/usr/bin/env python3
"""Reassemble both AgriLink copies and the dealer's five-band map."""
from collections import defaultdict, Counter
from pathlib import Path
import json
import numpy as np
from PIL import Image
from shapely.geometry import shape
from shapely import contains_xy
from sklearn.cluster import KMeans

ROOT=Path(__file__).parent
frames=[json.loads(line) for line in (ROOT/'agrilink_frames_0641.jsonl').read_text().splitlines()]
capture_starts=np.array([c['core:sample_start'] for c in
                         json.loads((ROOT/'szot_sdr_0641.sigmf-meta').read_text())['captures']])
iq=np.memmap(ROOT/'szot_sdr_0641.sigmf-data',dtype=np.int8,mode='r').reshape(-1,2)
# AGC adds a sizable noise floor. Measure mean-square signal in the captured
# preamble rather than comparing single coherent FFT peaks.
strength=np.zeros(len(capture_starts))
for idx,start in enumerate(capture_starts):
    preamble=iq[start+8000:start+11000].astype(float)
    strength[idx]=np.mean(preamble*preamble)
pairs=defaultdict(list)
for meta in frames:
    packet=bytes.fromhex(meta['payload'])
    if len(packet)==136 and packet[:2]==b'AL' and packet[5:6]==b'D':
        pairs[(packet[6],packet[7])].append((meta,packet))
assert len(pairs)==640 and all(len(v)==2 for v in pairs.values())
arrays=np.zeros((4,5,128,128),np.uint8)
for (channel,row),duplicates in pairs.items():
    first,second=duplicates
    best=max(duplicates,key=lambda pair:strength[pair[0]['index']])
    fec=min(duplicates,key=lambda pair:pair[0]['bad_fec'])
    for array,pair in zip(arrays,(first,second,best,fec)):
        array[channel,row]=np.frombuffer(pair[1][8:136],np.uint8)
np.save(ROOT/'agrilink_tiles.npy',arrays)
print('RSSI picks second copy',sum(max(v,key=lambda pair:strength[pair[0]['index']]) is v[1] for v in pairs.values()),'of',len(pairs))

dealer_bytes=(ROOT/'dealer_frames_0705.bin').read_bytes()
assert len(dealer_bytes)==1281*73
dealer=np.zeros((5,128,128),np.uint8)
seen=np.zeros((5,128,2),bool)
for idx in range(1,1281):
    packet=dealer_bytes[idx*73:(idx+1)*73]
    assert packet[:3]==b'JRM'
    channel,row,half=packet[3:6]
    assert channel<5 and row<128 and half<2 and not seen[channel,row,half]
    dealer[channel,row,half*64:(half+1)*64]=np.frombuffer(packet[7:71],np.uint8)
    seen[channel,row,half]=True
assert seen.all()
np.save(ROOT/'dealer_tile.npy',dealer)
print('dealer range',dealer.min(),dealer.max())

features=json.loads((ROOT/'szotyola_parcels_2025.geojson').read_text())['features']
y,x=np.mgrid[:128,:128]
parcel_masks=[]
for f in features:
    mask=contains_xy(shape(f['geometry']),x+.5,y+.5)
    if np.count_nonzero(mask)>0:
        parcel_masks.append((f['properties'],mask))
print('west parcels',len(parcel_masks))
east_masks=[]
for f in features:
    mask=contains_xy(shape(f['geometry']),x+128.5,y+.5)
    if np.count_nonzero(mask)>0:
        east_masks.append((f['properties'],mask))
print('east parcels',len(east_masks))

def ndvi(tile,nir,red):
    a=tile[nir].astype(float);b=tile[red].astype(float)
    return (a-b)/(a+b+1e-9)

for label,tile,nir,red in [('legit1',arrays[0],3,2),('legit2',arrays[1],3,2),('mast',arrays[2],0,1),('source',arrays[3],3,2)]:
    n=ndvi(tile,nir,red)
    print('\n',label)
    for props,mask in parcel_masks:
        if props['crop_2025']=='napraforgó':
            print(props['parcel'],round(float(np.median(n[mask])),3),end='; ')
    print()
    image=(np.clip((n+1)/2,0,1)*255).astype(np.uint8)
    Image.fromarray(image).resize((512,512),Image.Resampling.NEAREST).save(ROOT/f'ndvi_{label}.png')

mast_ndvi=ndvi(arrays[2],0,1)
sprayed=[(props['parcel'],mask) for props,mask in parcel_masks
         if props['crop_2025']=='napraforgó' and np.median(mast_ndvi[mask])<.44]
print('brown sunflower parcels:',[name for name,_ in sprayed])
assert len(sprayed)==6
assert all(np.median(ndvi(arrays[2],3,2)[mask])>=.44 for _,mask in sprayed)
model=KMeans(n_clusters=7,random_state=42,n_init=10)
classes=model.fit_predict(dealer.reshape(5,-1).T.astype(float)).reshape(128,128)
exclusive=[]
for class_id in range(7):
    holders=[(props['parcel'],int((classes[mask]==class_id).sum()))
             for props,mask in east_masks if int((classes[mask]==class_id).sum())>=5]
    if len(holders)==1:
        exclusive.append((class_id,holders[0]))
print('exclusive classes within east-block parcels:',exclusive)
night_targets={holder[0] for _,holder in exclusive}
assert night_targets=={'SZ4TE4'}
flag='GAIANSPACE{'+'-'.join(name for name,_ in sprayed)+'_'+night_targets.pop()+'}'
print(flag)
