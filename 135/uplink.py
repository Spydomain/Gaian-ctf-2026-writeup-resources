import numpy as np
from scipy import signal

raw=np.memmap('vela_band_0347.sigmf-data',dtype=np.int8)
fs=1999999.;center=433549995.;freq=433900000.
for tag,t0 in [('request',16.61),('early_request',4.14),('late_request',39.64)]:
    i=int(t0*fs);n=int(.14*fs)
    z=raw[2*i:2*(i+n):2].astype(np.float32)+1j*raw[2*i+1:2*(i+n):2].astype(np.float32)
    z*=np.exp(-2j*np.pi*(freq-center)*np.arange(i,i+n)/fs).astype(np.complex64)
    z=signal.resample_poly(z,1,4)
    np.save(f'{tag}.npy',z.astype(np.complex64))
    print(tag,len(z),max(abs(z)))
