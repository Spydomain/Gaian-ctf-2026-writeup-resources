import numpy as np
from scipy import signal

raw=np.memmap('vela_band_0302.sigmf-data',dtype=np.int8)
fs=1999999.;center=433549995.;freq=433175000.
starts=[2.76,5.98,9.42,12.68,16.00,19.26,22.68,25.94,29.28,32.48,36.24,39.54]
for j,start in enumerate(starts):
    t0=start-.1;i=int(t0*fs);n=min(int(.56*fs),raw.size//2-i)
    z=raw[2*i:2*(i+n):2].astype(np.float32)+1j*raw[2*i+1:2*(i+n):2].astype(np.float32)
    z*=np.exp(-2j*np.pi*(freq-center)*np.arange(i,i+n)/fs).astype(np.complex64)
    z=signal.resample_poly(z,1,16)
    np.save(f'burst_{j:02d}.npy',z.astype(np.complex64))
    print(j,t0,len(z),max(abs(z)))
