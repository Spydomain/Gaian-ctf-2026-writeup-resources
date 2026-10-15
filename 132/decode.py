import numpy as np

z=np.load('target4s.npy')[::2]
fs=1999999/16; N=1024; M=1024
n=np.arange(N);t=n/fs;T=N/fs
ref=np.exp(-2j*np.pi*(-62500*t+125000/(2*T)*t*t))
start=470434//2+11
pstart=start+16*N+N//4
q=np.array([z[pstart+i*N:pstart+(i+1)*N]*ref for i in range(86)])
F=np.fft.fft(q,axis=1); peaks=np.argmax(abs(F),axis=1)

def encode(nib,cr):
    d3,d2,d1,d0=[(nib>>i)&1 for i in (3,2,1,0)]
    p1=d3^d2^d0; p2=d3^d1^d0; p3=d2^d1^d0
    p4=d3^d2^d1^d0; p5=d3^d2^d1
    return {1:(p4<<4)|nib,2:(p5<<5)|(p3<<4)|nib,3:(p2<<6)|(p5<<5)|(p3<<4)|nib,4:(p1<<7)|(p2<<6)|(p5<<5)|(p3<<4)|nib}[cr]

def decode(offset):
    words=[];errors=[]
    for first,count,rows,cr,reduced in [(0,8,8,4,True)]+[(8+6*i,6,10,2,False) for i in range(13)]:
        block=peaks[first:first+count]
        vals=[]
        for p in block:
            b=((int(p)-offset)%M)//(4 if reduced else 1)
            vals.append(b^(b>>1))
        for k in range(rows):
            cw=sum(((vals[m]>>((k-m)%rows))&1)<<m for m in range(count))
            candidates=[encode(x,cr) for x in range(16)]
            ds=[(cw^c).bit_count() for c in candidates]
            nib=int(np.argmin(ds));words.append(nib);errors.append(min(ds))
    raw=bytes(words[i]|(words[i+1]<<4) for i in range(0,len(words),2))
    seq=[];reg=0xff
    for _ in range(len(raw)):
        seq.append(reg);fb=((reg>>7)^(reg>>5)^(reg>>4)^(reg>>3))&1
        reg=((reg<<1)&255)|fb
    plain=bytes(x^s for x,s in zip(raw,seq))
    return words,errors,raw,plain

for off in [-3,-2,-1,0,1,2,3,4,5]:
    w,e,r,p=decode(off)
    print('offset',off,'errors',sum(e),'max',max(e),'first',e[:8],'raw',r[:20].hex(),'plain',repr(p[:70]))
