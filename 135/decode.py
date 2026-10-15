import numpy as np

fs=1999999/16;N=512;M=N
n=np.arange(N);t=n/fs;T=N/fs
ref=np.exp(-2j*np.pi*(-62500*t+125000/(2*T)*t*t))
target=np.load('target.npy');t0=15.3
starts=[15.494,16.884,17.480,18.076,18.663]

def enc(nib,cr):
    d3,d2,d1,d0=[(nib>>i)&1 for i in (3,2,1,0)]
    p1=d3^d2^d0;p2=d3^d1^d0;p3=d2^d1^d0
    p4=d3^d2^d1^d0;p5=d3^d2^d1
    return {1:(p4<<4)|nib,2:(p5<<5)|(p3<<4)|nib,3:(p2<<6)|(p5<<5)|(p3<<4)|nib,4:(p1<<7)|(p2<<6)|(p5<<5)|(p3<<4)|nib}[cr]

def block_decode(peaks,off,rows,cr,reduced):
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

def get_peaks(x,t_start,limit):
    i0=int((t_start-t0-.012)*fs);i1=int((t_start-t0+.01)*fs)
    ix=np.where(abs(x[i0:i1])>1)[0]
    s=i0+ix[0]
    q=x[s:s+N]*ref;p=int(np.argmax(abs(np.fft.fft(q))))
    d=(-p)%N
    if d>N//2:d-=N
    s+=d
    pre=np.argmax(abs(np.fft.fft(np.array([x[s+i*N:s+(i+1)*N]*ref for i in range(14)]),axis=1)),axis=1)
    ps=s+16*N+N//4
    limit=min(limit,(len(x)-ps)//N)
    q=np.array([x[ps+i*N:ps+(i+1)*N]*ref for i in range(limit)])
    F=np.fft.fft(q,axis=1)
    peaks=np.argmax(abs(F),axis=1)
    ratios=np.max(abs(F),axis=1)/np.sqrt(np.mean(abs(F)**2,axis=1))
    return s,pre,peaks,ratios

def decode_packet(peaks):
    options=[]
    for off in range(-1,4):
        first,e1=block_decode(peaks[:8],off,7,4,True)
        length=first[0]*16+first[1]
        cr=first[2]>>1;crc=first[2]&1
        if cr not in (1,2,3,4) or length>200:continue
        need=2*(length+2*crc)-2
        groups=(need+8)//9
        nsym=8+groups*(4+cr)
        if nsym>len(peaks):continue
        words=first.copy();errors=e1.copy()
        for g in range(groups):
            lo=8+g*(4+cr);hi=lo+4+cr
            w,e=block_decode(peaks[lo:hi],off,9,cr,False)
            words.extend(w);errors.extend(e)
        ns=2*(length+2*crc)
        payload=words[5:5+ns]
        raw=bytes(payload[i]|(payload[i+1]<<4) for i in range(0,len(payload)-1,2))
        reg=255;plain=[]
        for b in raw:
            plain.append(b^reg)
            fb=((reg>>7)^(reg>>5)^(reg>>4)^(reg>>3))&1
            reg=((reg<<1)&255)|fb
        options.append((sum(errors),off,length,cr,crc,nsym,bytes(plain),errors))
    return min(options,key=lambda q:q[0]) if options else None

if __name__ == '__main__':
    for j,start in enumerate(starts):
        s,pre,peaks,ratios=get_peaks(target,start,115)
        result=decode_packet(peaks)
        print(j,'start',round(t0+s/fs,6),'sync',pre[12:14].tolist(),'result',result[:6] if result else None)
        if result:
            err,off,length,cr,crc,nsym,data,errors=result
            print('  errors',[(i,v) for i,v in enumerate(errors) if v][:20],'data',data.hex(),'ascii',repr(data))
            with open(f'packet_{j}.bin','wb') as f:f.write(data)
