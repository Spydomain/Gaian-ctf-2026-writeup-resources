#!/usr/bin/env python3
"""Map the anchor bite onto UTC, including asymmetric LoRa airtimes."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from fractions import Fraction
import csv,json,math,re,struct
import numpy as np
from scipy.optimize import linprog

ROOT=Path(__file__).resolve().parent
REFERENCE=datetime(2041,11,4,16,47,tzinfo=timezone.utc)
def seconds(text):
    return (datetime.fromisoformat(text.replace('Z','+00:00'))-REFERENCE).total_seconds()
def iso(value):
    return (REFERENCE+timedelta(seconds=float(value))).isoformat(timespec='microseconds').replace('+00:00','Z')

def airtime(sf,payload_bytes,bw=125000,cr=1,preamble=8,explicit=True,crc=True):
    ts=Fraction(2**sf,bw)
    de=int(ts>Fraction(16,1000))
    numerator=8*payload_bytes-4*sf+28+16*int(crc)-20*int(not explicit)
    denominator=4*(sf-2*de)
    blocks=max(math.ceil(Fraction(numerator,denominator)),0)
    symbols=8+blocks*(cr+4)
    return ts*(Fraction(preamble)+Fraction(17,4)+symbols)

up=float(airtime(7,5));down=float(airtime(11,14))
print(f'Ping airtime: {up*1000:.3f} ms; reply airtime: {down*1000:.3f} ms')
event_log=(ROOT/'lander_events.log').read_text()
bite=int(re.search(r'^\s*(\d+)\s+anchor BITE:',event_log,re.M).group(1))
rows=[]
for line in (ROOT/'mothership_tt.log').read_text().splitlines():
    if line.startswith('#') or not line.strip():continue
    seq,T1,T4,rssi,snr,crc,hx=line.split()
    if crc!='ok':continue
    magic,vehicle,wire_seq,command,t2,t3=struct.unpack('<2sBHBII',bytes.fromhex(hx))
    assert magic==b'TT' and vehicle==111 and wire_seq==int(seq)
    assert 0<=t3-t2<1000
    rows.append({'seq':int(seq),'T1':seconds(T1),'T4':seconds(T4),'t2':t2,'t3':t3,'command':command})

# Each pair of matching clock readings is RX-done on the uplink and
# TX-start on the downlink. Strip the known airtime from each direction.
# Average the two correspondences to estimate a constant offset and skew.
local=np.array([((r['t2']+r['t3'])/2-bite)/1000 for r in rows])
utc=np.array([(r['T1']+up+r['T4']-down)/2 for r in rows])
fit=np.linalg.lstsq(np.column_stack([np.ones(len(local)),local]),utc,rcond=None)[0]
residual=utc-(fit[0]+fit[1]*local)
# Reject the small number of long-RTT scheduler outliers, then refit.
keep=abs(residual-np.median(residual))<.0015
fit=np.linalg.lstsq(np.column_stack([np.ones(keep.sum()),local[keep]]),utc[keep],rcond=None)[0]
print(f'Valid exchanges: {len(rows)}; robust fit uses {int(keep.sum())}')
print(f'UTC seconds per OBC second: {fit[1]:.12f}')
print(f'Bite estimate: {iso(fit[0])}')
print(f'Fit residual RMS: {np.std(utc[keep]-(fit[0]+fit[1]*local[keep]))*1000:.3f} ms')

# Also bound the answer without assuming the remaining delays are symmetric.
# Causality gives UTC(t2) >= T1 + ping airtime and
# UTC(t3) <= T4 - reply airtime. Allow one full OBC tick of timestamp
# quantisation conservatively. Affine UTC(x) = a + b*x; x=0 at the bite.
A=[];B=[];tick=.001
for r in rows:
    x2=(r['t2']-bite)/1000;x3=(r['t3']-bite)/1000
    A.append([-1,-(x2+tick)]);B.append(-(r['T1']+up))
    A.append([1,x3-tick]);B.append(r['T4']-down)
minimum=linprog([1,0],A_ub=A,b_ub=B,bounds=[(None,None),(0,None)],method='highs')
maximum=linprog([-1,0],A_ub=A,b_ub=B,bounds=[(None,None),(0,None)],method='highs')
assert minimum.success and maximum.success
lo,hi=minimum.x[0],maximum.x[0]
print(f'Causal bite interval: {iso(lo)} .. {iso(hi)}')
frames=list(csv.DictReader((ROOT/'hover_frames.csv').open()))
frame_ids=np.array([int(f['frame']) for f in frames])
starts=np.array([seconds(f['exposure_start_utc']) for f in frames])
assert np.all(np.diff(starts)>0) and np.all(np.diff(frame_ids)>0)
assert np.max(abs((starts-starts[0])-(frame_ids-frame_ids[0])*.05))<1e-8
# Preserve the camera counter even where an indexed frame was lost.
frame_base=int(frame_ids[0]);time_base=float(starts[0]);period=.05
def first_after(t):return frame_base+math.floor((t-time_base)/period)+1
assert first_after(lo)==first_after(hi)
answer=first_after(fit[0]);assert answer==first_after(lo)
index={int(f['frame']):f for f in frames}
print('Previous frame:',index.get(answer-1,{'frame':f'{answer-1:07d}','lost':True}))
print('First frame after bite:',index.get(answer,{'frame':f'{answer:07d}','lost':True}))
flag=f'GAIANSPACE{{{answer:07d}}}'
print(flag)
(ROOT/'flag.txt').write_text(flag+'\n')
(ROOT/'timing_result.json').write_text(json.dumps({'flag':flag,'bite_obc_ms':bite,
    'bite_estimate_utc':iso(fit[0]),'bite_causal_interval_utc':[iso(lo),iso(hi)],
    'utc_seconds_per_obc_second':float(fit[1]),'ping_airtime_ms':up*1000,
    'reply_airtime_ms':down*1000,'preceding_frame':index.get(answer-1),
    'selected_frame':index.get(answer)},indent=2)+'\n')
