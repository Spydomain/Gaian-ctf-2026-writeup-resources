import numpy as np

fs=1999999/16; N=512; M=N
n=np.arange(N);t=n/fs;T=N/fs
ref=np.exp(-2j*np.pi*(-62500*t+125000/(2*T)*t*t))
starts=[2.76,5.98,9.42,12.68,16.00,19.26,22.68,25.94,29.28,32.48,36.24,39.54]

def enc(nib,cr):
    d3,d2,d1,d0=[(nib>>i)&1 for i in (3,2,1,0)]
    p1=d3^d2^d0;p2=d3^d1^d0;p3=d2^d1^d0
    p4=d3^d2^d1^d0;p5=d3^d2^d1
    return {1:(p4<<4)|nib,4:(p1<<7)|(p2<<6)|(p5<<5)|(p3<<4)|nib}[cr]

def decode_bins(peaks,off=1):
    words=[];errors=[]
    blocks=[(0,8,7,4,True)]+[(8+5*i,5,9,1,False) for i in range(11)]
    for first,count,rows,cr,reduced in blocks:
        vals=[]
        for p in peaks[first:first+count]:
            b=((int(p)-off)%M)//(4 if reduced else 1)
            vals.append(b^(b>>1))
        for k in range(rows):
            cw=sum(((vals[m]>>((k-m)%rows))&1)<<m for m in range(count))
            ds=[(cw^enc(x,cr)).bit_count() for x in range(16)]
            words.append(int(np.argmin(ds)));errors.append(min(ds))
    raw=bytes(words[i]|(words[i+1]<<4) for i in range(5,len(words)-1,2))
    reg=0xff;plain=[]
    for b in raw:
        plain.append(b^reg)
        fb=((reg>>7)^(reg>>5)^(reg>>4)^(reg>>3))&1
        reg=((reg<<1)&255)|fb
    return words,errors,raw,bytes(plain)

def demod(x):
    ix=np.where(abs(x[int(.06*fs):int(.3*fs)])>20)[0]
    s=int(.06*fs)+ix[0]
    q=np.array([x[s+i*N:s+(i+1)*N]*ref for i in range(12)])
    p=int(np.argmax(abs(np.fft.fft(q[0]))))
    d=(-p)%N
    if d>N//2:d-=N
    s+=d
    pre=np.argmax(abs(np.fft.fft(np.array([x[s+i*N:s+(i+1)*N]*ref for i in range(14)]),axis=1)),axis=1)
    ps=s+16*N+N//4
    q=np.array([x[ps+i*N:ps+(i+1)*N]*ref for i in range(63)])
    F=np.fft.fft(q,axis=1)
    peaks=np.argmax(abs(F),axis=1)
    ratios=np.max(abs(F),axis=1)/np.sqrt(np.mean(abs(F)**2,axis=1))
    return s,pre,peaks,ratios

all_raw=[]
for j,start in enumerate(starts):
    x=np.load(f'burst_{j:02d}.npy')
    s,pre,peaks,ratios=demod(x)
    best=[]
    for off in range(-1,4):
        w,e,r,p=decode_bins(peaks,off)
        best.append((sum(e),off,w,e,r,p))
    _,off,w,e,r,p=min(best,key=lambda v:v[0])
    print(j,'start',round(start-.1+s/fs,6),'sync',pre[12:14].tolist(),'off',off,'err',sum(e),'header',w[:7],'raw',r.hex(),'plain',repr(p[:53]))
    all_raw.append(r)
np.save('frames.npy',np.array([list(x) for x in all_raw],dtype=np.uint8))
