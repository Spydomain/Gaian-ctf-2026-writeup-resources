import numpy as np
from scipy import signal

raw=np.memmap('vela_wide_0212.sigmf-data',dtype=np.int8)
fs=2999999.0; fcenter=433999996.0
t0=14.7;dur=.9;i=int(t0*fs);n=int(dur*fs)
z=raw[2*i:2*(i+n):2].astype(np.float32)+1j*raw[2*i+1:2*(i+n):2].astype(np.float32)
for freq in np.arange(433175000,434675001,150000):
    x=z*np.exp(-2j*np.pi*(freq-fcenter)*np.arange(i,i+n)/fs).astype(np.complex64)
    x=signal.resample_poly(x,1,24)
    np.save(f'channel_{int(freq/1000)}.npy',x.astype(np.complex64))
    print(freq/1e6,len(x),abs(x).max())
