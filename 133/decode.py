import numpy as np

sym=np.load('symbols.npy')[:118]
peaks=sym[:,3].astype(int)
M=512

def encode(nib,cr):
    d3,d2,d1,d0=[(nib>>i)&1 for i in (3,2,1,0)]
    p1=d3^d2^d0;p2=d3^d1^d0;p3=d2^d1^d0
    p4=d3^d2^d1^d0;p5=d3^d2^d1
    return {1:(p4<<4)|nib,4:(p1<<7)|(p2<<6)|(p5<<5)|(p3<<4)|nib}[cr]

def decode(off):
    words=[];errors=[]
    blocks=[(0,8,7,4,True)]+[(8+5*i,5,9,1,False) for i in range(22)]
    for first,count,rows,cr,reduced in blocks:
        vals=[]
        for p in peaks[first:first+count]:
            b=((int(p)-off)%M)//(4 if reduced else 1)
            vals.append(b^(b>>1))
        for k in range(rows):
            cw=sum(((vals[m]>>((k-m)%rows))&1)<<m for m in range(count))
            candidates=[encode(x,cr) for x in range(16)]
            ds=[(cw^c).bit_count() for c in candidates]
            nib=int(np.argmin(ds));words.append(nib);errors.append(min(ds))
    # Explicit LoRa header: five nibbles, then user payload low nibble first.
    payload=words[5:]
    raw=bytes(payload[i]|(payload[i+1]<<4) for i in range(0,len(payload)-1,2))
    seq=[];reg=0xff
    for _ in range(len(raw)):
        seq.append(reg);fb=((reg>>7)^(reg>>5)^(reg>>4)^(reg>>3))&1
        reg=((reg<<1)&255)|fb
    plain=bytes(x^s for x,s in zip(raw,seq))
    return words,errors,raw,plain

for off in range(-2,5):
    w,e,r,p=decode(off)
    print('off',off,'errors',sum(e),'header',w[:7],'first',e[:7],'raw',r[:12].hex(),'plain',repr(p[:110]))
