#!/usr/bin/env python3
import json,re,csv
from pathlib import Path
import numpy as np
import tifffile
import shapely
from scipy.special import logsumexp

ROOT=Path(__file__).resolve().parent
with tifffile.TiffFile(ROOT/'office_check_20250704.tif') as tf:
    image=tf.asarray().astype(float)
    scale=tf.pages[0].tags['ModelPixelScaleTag'].value
    tie=tf.pages[0].tags['ModelTiepointTag'].value
h,w,bands=image.shape
xx=tie[3]+(np.arange(w)+.5)*scale[0]
yy=tie[4]-(np.arange(h)+.5)*scale[1]
X,Y=np.meshgrid(xx,yy)

def mask(geometry):
    return shapely.contains_xy(shapely.geometry.shape(geometry),X,Y)

def stats(geometry):
    pixels=image[mask(geometry)]
    return {'n':len(pixels),'mean':pixels.mean(0),'cov':np.cov(pixels,rowvar=False,ddof=1)}

fields=json.loads((ROOT/'training_fields.geojson').read_text())['features']
classes={}
for f in fields:
    p=f['properties'];s=stats(f['geometry']);assert s['n']==p['pixels']
    classes[p['class']]=s
    print(p['class'],'n',s['n'],'mean',np.round(s['mean'],3),'cov eig min',np.linalg.eigvalsh(s['cov']).min())

# Verify that our pixel selection reproduces every supplied class statistic.
text=(ROOT/'office_training.sta').read_text()
for block in text.split('CLASS ')[1:]:
    rows=block.splitlines();name=rows[0].split()[0]
    mean=np.array([float(v) for v in rows[1].split()[1:]])
    cov=np.array([[float(v) for v in line.split()[1:]] for line in rows[2:7]])
    assert np.max(abs(mean-classes[name]['mean']))<.000501
    assert np.max(abs(cov-classes[name]['cov']))<.000501
print('All four supplied mean/covariance matrices reproduced within their rounding precision.')

names=list(classes)
pixels=image.reshape(-1,bands)
scores=[]
for name in names:
    s=classes[name];delta=pixels-s['mean'];icov=np.linalg.inv(s['cov'])
    md=np.einsum('ni,ij,nj->n',delta,icov,delta)
    scores.append(-.5*(md+np.linalg.slogdet(s['cov'])[1]+bands*np.log(2*np.pi)))
scores=np.stack(scores,axis=-1).reshape(h,w,len(names))
label=scores.argmax(-1)
prob=np.exp(scores-logsumexp(scores,axis=-1,keepdims=True))
office_idx=[i for i,name in enumerate(names) if name!='kukorica']
office_labels=np.asarray(office_idx)[scores[:,:,office_idx].argmax(-1)]

claims={}
for line in (ROOT/'decoded_frames.jsonl').read_text().splitlines():
    frame=json.loads(line)
    if not (frame['header_ok'] and frame['crc_ok']):continue
    payload=bytes.fromhex(frame['payload'])
    text=payload[4:].decode('ascii')
    if not re.fullmatch(r'\d\d;MZH-\d{4};\w+;\d+\.\d{2};[A-Z0-9]{4}',text):continue
    seq,parcel,declared,area,code=text.split(';')
    claim={'order':int(seq),'parcel':parcel,'declared':declared,'area_ha':float(area),'code':code}
    if int(seq) in claims:assert claims[int(seq)]==claim
    claims[int(seq)]=claim
assert sorted(claims)==list(range(1,31))
parcels={f['properties']['parcel']:f for f in json.loads((ROOT/'parcels.geojson').read_text())['features']}
results=[]
for order,claim in sorted(claims.items()):
    parcel=parcels[claim['parcel']];pmask=mask(parcel['geometry'])
    counts=np.bincount(label[pmask],minlength=len(names));office_counts=np.bincount(office_labels[pmask],minlength=len(names))
    actual=names[counts.argmax()];office=names[office_counts.argmax()]
    result={**claim,'actual':actual,'office':office,'false':actual!=claim['declared'],
        'pixels':int(pmask.sum()),'fraction':float(counts.max()/counts.sum()),
        'class_fractions':{name:float(count/counts.sum()) for name,count in zip(names,counts)},
        'mean_class_probabilities':dict(zip(names,prob[pmask].mean(0).tolist()))}
    assert abs(claim['area_ha']-parcel['properties']['area_ha'])<.0001
    results.append(result)
    print(f"{order:02d} {claim['code']} {claim['parcel']} declared={claim['declared']:<8} office={office:<8} restored={actual:<8} share={result['fraction']:.3f} false={result['false']}")
(ROOT/'claims_analysis.json').write_text(json.dumps(results,indent=2)+'\n')
with open(ROOT/'claims_analysis.csv','w') as f:
    columns=['order','code','parcel','declared','office','actual','fraction','false']
    out=csv.DictWriter(f,columns);out.writeheader();out.writerows({k:r[k] for k in columns} for r in results)
flag='GAIANSPACE{'+'-'.join(r['code'] for r in results if r['false'])+'}'
(ROOT/'flag.txt').write_text(flag+'\n')
print(flag)
