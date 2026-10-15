import numpy as np
from scipy.signal import resample_poly

fs=1999999/8;N=128;M=N
n=np.arange(N);t=n/fs;T=N/fs
ref=np.exp(-2j*np.pi*(-125000*t+250000/(2*T)*t*t))

def enc(nib,cr):
    d3,d2,d1,d0=[(nib>>i)&1 for i in (3,2,1,0)]
    p1=d3^d2^d0;p2=d3^d1^d0;p3=d2^d1^d0
    p4=d3^d2^d1^d0;p5=d3^d2^d1
    return {1:(p4<<4)|nib,2:(p5<<5)|(p3<<4)|nib,3:(p2<<6)|(p5<<5)|(p3<<4)|nib,4:(p1<<7)|(p2<<6)|(p5<<5)|(p3<<4)|nib}[cr]

def block(peaks,off,rows,cr,reduced):
    vals=[]
    for p in peaks:
        b=((int(p)-off)%M)//(4 if reduced else 1)
        vals.append(b^(b>>1))
    words=[];errors=[]
    for k in range(rows):
        cw=sum(((vals[m]>>((k-m)%rows))&1)<<m for m in range(len(peaks)))
        ds=[(cw^enc(x,cr)).bit_count() for x in range(16)]
        words.append(int(np.argmin(ds)));errors.append(min(ds))
    return words,errors

def decode(peaks,off):
    first,e1=block(peaks[:8],off,5,4,True)
    length=first[0]*16+first[1];cr=first[2]>>1;crc=first[2]&1
    if cr not in range(1,5) or length>200:return None
    need=2*(length+2*crc);groups=(need+6)//7;nsym=8+groups*(4+cr)
    if nsym>len(peaks):return None
    words=first.copy();errors=e1.copy()
    for g in range(groups):
        lo=8+g*(4+cr);hi=lo+4+cr
        w,e=block(peaks[lo:hi],off,7,cr,False)
        words.extend(w);errors.extend(e)
    payload=words[5:5+need]
    raw=bytes(payload[i]|payload[i+1]<<4 for i in range(0,len(payload)-1,2))
    reg=255;plain=[]
    for b in raw:
        plain.append(b^reg)
        fb=((reg>>7)^(reg>>5)^(reg>>4)^(reg>>3))&1
        reg=((reg<<1)&255)|fb
    return sum(errors),length,cr,crc,nsym,bytes(plain),errors,first

for tag,t0 in [('request',16.61),('early_request',4.14),('late_request',39.64)]:
    x=resample_poly(np.load(tag+'.npy'),1,2)
    s=np.where(abs(x)>10)[0][0]
    candidates=[]
    for shift in range(-20,20):
        ps=s+shift+12*N+N//4
        q=np.array([x[ps+i*N:ps+(i+1)*N]*ref for i in range(60)])
        peaks=np.argmax(abs(np.fft.fft(q,axis=1)),axis=1)
        for off in range(-1,4):
            result=decode(peaks,off)
            if result:candidates.append((result[0],shift,off,result))
    err,shift,off,r=min(candidates,key=lambda v:v[0])
    print(tag,'start',t0+(s+shift)/fs,'offset',off,'errors',err,'header',r[-1],'result',r[:5],'data',r[5].hex(),'ascii',repr(r[5]))
    with open(f'{tag}.bin','wb') as f:f.write(r[5])
