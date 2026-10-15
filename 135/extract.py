import numpy as np
from scipy import signal

raw=np.memmap('vela_band_0347.sigmf-data',dtype=np.int8)
fs=1999999.;center=433549995.;freq=433175000.
for tag,t0,dur in [('target',15.3,3.8),('early',2.8,2.2),('late',38.3,2.0)]:
    i=int(t0*fs);n=min(int(dur*fs),raw.size//2-i)
    z=raw[2*i:2*(i+n):2].astype(np.float32)+1j*raw[2*i+1:2*(i+n):2].astype(np.float32)
    z*=np.exp(-2j*np.pi*(freq-center)*np.arange(i,i+n)/fs).astype(np.complex64)
    z=signal.resample_poly(z,1,16)
    np.save(f'{tag}.npy',z.astype(np.complex64))
    print(tag,t0,len(z),max(abs(z)))
