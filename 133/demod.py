import numpy as np

fs=2999999/24; N=512; M=N
freqs=list(range(433175,434676,150))
channels={f:np.load(f'channel_{f}.npy') for f in freqs}
s=16116; pstart=s+16*N+N//4
n=np.arange(N);t=n/fs;T=N/fs
ref=np.exp(-2j*np.pi*(-62500*t+125000/(2*T)*t*t))

rows=[]
for j in range(150):
    i=pstart+j*N
    if i+N>len(next(iter(channels.values()))):break
    pw={f:np.mean(abs(x[i:i+N])**2) for f,x in channels.items()}
    f=max(pw,key=pw.get)
    q=channels[f][i:i+N]*ref
    F=np.fft.fft(q)
    p=int(np.argmax(abs(F)))
    ratio=float(np.max(abs(F))/np.sqrt(np.mean(abs(F)**2)))
    rows.append((j,14.7+i/fs,f,p,ratio,pw[f]))

for j,time,f,p,r,pw in rows:
    print(f'{j:3d} {time:.6f} {f:6d} {p:3d} {r:4.1f} {pw:5.2f}')
np.save('symbols.npy',np.array(rows))
