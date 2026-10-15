#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timedelta,timezone
import struct,json
ROOT=Path(__file__).resolve().parent
DATA_POSITIONS=[p for p in range(1,39) if p not in (1,2,4,8,16,32)]

def encode(data):
    cw=sum(((data>>i)&1)<<(p-1) for i,p in enumerate(DATA_POSITIONS))
    for k in (1,2,4,8,16,32):
        if sum((cw>>(p-1))&1 for p in range(1,39) if p&k)%2:cw|=1<<(k-1)
    if cw.bit_count()%2:cw|=1<<38
    return cw

def decode(cw):
    assert cw>>39==0
    raw=cw;syndrome=0
    for p in range(1,39):
        if cw>>(p-1)&1:syndrome^=p
    odd=cw.bit_count()%2
    status='clean';correction=None
    if syndrome and not odd:status='uncorrectable'
    elif odd:
        correction=syndrome or 39
        if not 1<=correction<=39:status='uncorrectable'
        else:cw^=1<<(correction-1);status='corrected'
    data=sum(((cw>>(p-1))&1)<<i for i,p in enumerate(DATA_POSITIONS))
    if status!='uncorrectable':assert encode(data)==cw
    return {'raw':raw,'data':data,'status':status,'syndrome':syndrome,'overall_odd':bool(odd),'correction':correction}

blob=(ROOT/'keel_dump.bin').read_bytes()
magic,version,nrows,nwords,nbanks,week,sow,_=struct.unpack('<8sHHHHHI10s',blob[:32])
assert (magic,version,nwords,nbanks)==(b'KEELDMP1',1,2,3)
assert len(blob)==32+8*nrows*nwords*nbanks
banks=[]
for bank in range(nbanks):
    banks.append([decode(struct.unpack_from('<Q',blob,32+8*(bank*nrows*nwords+i))[0]) for i in range(nrows*nwords)])

# A and C were shielded and have only sporadic errors. B has a long history
# of permanent, repeatedly miscorrected words, including nonzero erased rows.
words=[]
for i,(a,c) in enumerate(zip(banks[0],banks[2])):
    good=[v for v in (a,c) if v['status']!='uncorrectable']
    assert good and all(v['data']==good[0]['data'] for v in good)
    data=good[0]['data'];words.append(data)
    if a['status']=='uncorrectable':
        flips=[p+1 for p in range(39) if ((a['raw']^encode(data))>>p)&1]
        print(f'A row {i//2} word {i%2}: recovered from C; double-error positions {flips}')
        assert len(flips)==2

# The rollover is explicitly recorded in scrub.log: current raw week 0
# represents absolute week 1024, not the epoch in 2038.
assert 'CLOCK WEEK 1023 -> 0000' in (ROOT/'scrub.log').read_text()
epoch=datetime(2038,1,4,tzinfo=timezone.utc)
current_absolute_week=1024+week
current=epoch+timedelta(weeks=current_absolute_week,seconds=sow)
print('Dump UTC:',current.isoformat())
rows=[]
for row in range(nrows):
    word0,word1=words[2*row:2*row+2]
    if word0==word1==0:continue
    assert word0&3==0
    wk=word0>>22;sow=(word0>>2)&((1<<20)-1);dv=(word1>>16)/10;bid=(word1>>8)&255;thr=word1&255
    assert sow<604800
    # The old rows were already flown before this first rollover; future
    # rows have wrapped weeks and are within the approaching return window.
    absolute_week=wk if wk>week+512 else wk+1024
    ignition=epoch+timedelta(weeks=absolute_week,seconds=sow)
    item={'row':row,'week':wk,'absolute_week':absolute_week,'sow':sow,'ignition_utc':ignition.strftime('%Y-%m-%d %H:%M:%S'),'dv':f'{dv:.1f}','burn_id':f'0x{bid:02X}','thrusters':f'0x{thr:02X}'}
    rows.append(item);print(item)
eoi=[r for r in rows if r['burn_id']=='0x40'];assert len(eoi)==1
readback=eoi[0]['ignition_utc']+' '+eoi[0]['dv']
(ROOT/'burn_readback.txt').write_text(readback+'\n')
(ROOT/'recovered_table.json').write_text(json.dumps(rows,indent=2)+'\n')
print('KEEL primary insertion readback:',readback)
