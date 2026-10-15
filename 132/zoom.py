import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

raw=np.memmap('vela_band_0136.sigmf-data',dtype=np.int8)
fs=1999999.0
start=33.0; dur=4.0
i=int(start*fs); n=int(dur*fs)
z=raw[2*i:2*(i+n):2].astype(np.float32)+1j*raw[2*i+1:2*(i+n):2].astype(np.float32)
f0=433175000-433549995
z *= np.exp(-2j*np.pi*f0*np.arange(i,i+n)/fs).astype(np.complex64)
z=signal.resample_poly(z,1,8)
fs/=8
np.save('target4s.npy',z)
f,t,S=signal.spectrogram(z,fs,nperseg=512,noverlap=384,return_onesided=False,mode='magnitude')
S=np.fft.fftshift(S,axes=0); f=np.fft.fftshift(f)
plt.figure(figsize=(15,7))
plt.imshow(20*np.log10(S+1e-5),extent=[t[0]+start,t[-1]+start,f[0]/1000,f[-1]/1000],origin='lower',aspect='auto',vmin=-55,vmax=0)
plt.ylim(-100,100);plt.colorbar();plt.savefig('zoom.png',dpi=140)
print(len(z),np.max(np.abs(z)))
