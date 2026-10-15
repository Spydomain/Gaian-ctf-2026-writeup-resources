import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

path = 'vela_band_0136.sigmf-data'
raw = np.memmap(path, dtype=np.int8)
fs = 1999999.0
ns = raw.size // 2
print('samples', ns, 'duration', ns/fs)

# Average short spectra in each 0.1-second interval.
nfft = 4096
step = int(fs * .1)
rows = []
for base in range(0, ns-step, step):
    offsets = base + np.linspace(0, step-nfft, 12, dtype=int)
    ix = offsets[:,None] + np.arange(nfft)
    z = raw[2*ix].astype(np.float32) + 1j*raw[2*ix+1].astype(np.float32)
    spec = np.fft.fftshift(np.fft.fft(z*np.hanning(nfft), axis=1), axes=1)
    rows.append(np.mean(np.abs(spec)**2, axis=0))
P = np.array(rows)
np.savez_compressed('spectra.npz', P=P)
freqs = np.fft.fftshift(np.fft.fftfreq(nfft, 1/fs)) + 433549995
plt.figure(figsize=(16,8))
plt.imshow(10*np.log10(P.T + 1), origin='lower', aspect='auto', extent=[0, len(P)*.1, freqs[0]/1e6, freqs[-1]/1e6], vmin=25, vmax=65)
plt.colorbar(label='dB')
plt.xlabel('seconds from 01:36:45 UTC')
plt.ylabel('MHz')
plt.savefig('waterfall.png', dpi=140)
print('top mean frequencies', sorted(zip(P.mean(axis=0), freqs),reverse=True)[:20])
