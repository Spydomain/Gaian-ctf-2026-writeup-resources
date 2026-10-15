import numpy as np
import matplotlib.pyplot as plt

raw=np.memmap('vela_wide_0212.sigmf-data',dtype=np.int8)
fs=2999999.0; ns=raw.size//2
print('duration',ns/fs)
nfft=2048;step=int(fs*.01)
rows=[]
for base in range(0,ns-step,step):
    offsets=base+np.linspace(0,step-nfft,4,dtype=int)
    ix=offsets[:,None]+np.arange(nfft)
    z=raw[2*ix].astype(np.float32)+1j*raw[2*ix+1].astype(np.float32)
    F=np.fft.fftshift(np.fft.fft(z*np.hanning(nfft),axis=1),axes=1)
    rows.append(np.mean(abs(F)**2,axis=0))
P=np.asarray(rows,dtype=np.float32)
np.save('spectra.npy',P)
freq=np.fft.fftshift(np.fft.fftfreq(nfft,1/fs))+433999996
plt.figure(figsize=(16,8))
plt.imshow(10*np.log10(P.T+1),origin='lower',aspect='auto',extent=[0,len(P)*.01,freq[0]/1e6,freq[-1]/1e6],vmin=25,vmax=70)
plt.colorbar();plt.savefig('waterfall.png',dpi=150)
