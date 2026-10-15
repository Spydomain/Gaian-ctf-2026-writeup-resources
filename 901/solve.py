#!/usr/bin/env python3
"""Read 22 kHz DiSEqC pulse widths as MSB-first bytes with odd parity."""
from pathlib import Path
import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parent
sample_rate, audio = wavfile.read(ROOT / 'coax_tap_22k.wav')
assert sample_rate == 48_000
signal = audio.astype(float)
rms = np.sqrt(np.convolve(signal * signal, np.ones(12) / 12, mode='same'))
active = rms > 2000
edges = np.diff(active.astype(np.int8), prepend=0, append=0)
starts = np.flatnonzero(edges == 1)
ends = np.flatnonzero(edges == -1)
assert len(starts) == len(ends) and len(starts) % 9 == 0
assert np.max(np.abs(np.diff(starts) / sample_rate - 0.0015)) < 0.0001
duration_ms = (ends - starts) * 1000 / sample_rate
bits = [0 if duration > 0.9 else 1 for duration in duration_ms]
message = bytearray()
for start in range(0, len(bits), 9):
    symbol = bits[start:start + 9]
    assert sum(symbol) % 2 == 1  # DiSEqC odd parity.
    message.append(sum(symbol[bit] << (7 - bit) for bit in range(8)))
flag = message.decode('ascii')
assert flag.startswith('GAIANSPACE{') and flag.endswith('}')
print('Decoded bits:', len(bits), 'bytes:', len(message))
print(flag)
