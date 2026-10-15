#!/usr/bin/env python3
"""
LoRa demodulator for the tractor channel SDR capture.

Parameters from the Johnripper service manual:
  - Carrier: 433.400 MHz
  - SF: 7, BW: 500 kHz, CR: 4/5
  - Sync word: 0x2C
  - Preamble: 10 symbols
  - Implicit header (no radio header)
  - No radio CRC

The SDR capture is ci8 at 2 MHz sample rate, centered on 433.4 MHz.
"""

import numpy as np
import json
import struct
import sys

# LoRa parameters
SF = 7                # Spreading factor
BW = 500000           # Bandwidth in Hz
FS = 1999999          # Sample rate
N = 2**SF             # Number of bins = 128
CR = 1                # Coding rate offset (4/5 -> 1)
SYNC_WORD = 0x2C

# Symbol duration in samples
T_sym = N / BW        # = 128/500000 = 0.000256 s
N_samp = int(T_sym * FS)  # samples per symbol at the SDR sample rate

print(f"SF={SF}, BW={BW}, N={N}, T_sym={T_sym*1000:.3f}ms, N_samp={N_samp}")

def load_burst(data_file, sample_start, num_samples):
    """Load a burst of ci8 samples."""
    offset = sample_start * 2  # 2 bytes per sample (I + Q)
    with open(data_file, 'rb') as f:
        f.seek(offset)
        raw = f.read(num_samples * 2)
    iq = np.frombuffer(raw, dtype=np.int8).astype(np.float32)
    return iq[0::2] + 1j * iq[1::2]

def dechirp(samples, sf, bw, fs, is_downchirp=False):
    """
    Dechirp by mixing with a conjugate chirp, then FFT to find the peak bin.
    """
    n = 2**sf
    t_sym = n / bw
    n_samp = int(t_sym * fs)

    # Generate base chirp
    t = np.arange(n_samp) / fs
    if is_downchirp:
        # downchirp for dechirping upchirps
        phase = 2 * np.pi * (-bw/2 * t + bw/(2*t_sym) * t**2)
    else:
        # upchirp for dechirping downchirps
        phase = 2 * np.pi * (bw/2 * t - bw/(2*t_sym) * t**2)

    ref_chirp = np.exp(1j * phase)

    # Trim or pad samples
    if len(samples) < n_samp:
        samples = np.pad(samples, (0, n_samp - len(samples)))
    else:
        samples = samples[:n_samp]

    # Mix and FFT
    mixed = samples * ref_chirp
    # Resample to exactly N bins via FFT
    fft_result = np.fft.fft(mixed, n=n)
    magnitudes = np.abs(fft_result)
    peak_bin = np.argmax(magnitudes)

    return peak_bin, magnitudes[peak_bin] / np.mean(magnitudes)

def find_preamble(iq_data, sf, bw, fs):
    """
    Find the preamble in the IQ data: look for consecutive symbols with the same bin value.
    Returns the sample offset where the preamble starts.
    """
    n = 2**sf
    t_sym = n / bw
    n_samp = int(t_sym * fs)

    # Slide through, looking for repeated bins
    max_symbols = len(iq_data) // n_samp
    bins = []
    for i in range(min(max_symbols, 200)):
        chunk = iq_data[i*n_samp : (i+1)*n_samp]
        if len(chunk) < n_samp:
            break
        b, snr = dechirp(chunk, sf, bw, fs, is_downchirp=True)
        bins.append((b, snr))

    return bins

def demod_symbol(iq_data, offset, sf, bw, fs):
    """Demodulate one LoRa symbol at the given sample offset."""
    n = 2**sf
    t_sym = n / bw
    n_samp = int(t_sym * fs)

    chunk = iq_data[offset : offset + n_samp]
    if len(chunk) < n_samp // 2:
        return None, 0

    peak_bin, snr = dechirp(chunk, sf, bw, fs, is_downchirp=True)
    return peak_bin, snr

def demod_burst(iq_data, sf, bw, fs):
    """
    Demodulate an entire burst.
    Returns list of raw symbol values.
    """
    n = 2**sf
    t_sym = n / bw
    n_samp = int(t_sym * fs)

    max_symbols = len(iq_data) // n_samp
    symbols = []
    for i in range(max_symbols):
        chunk = iq_data[i*n_samp : (i+1)*n_samp]
        if len(chunk) < n_samp:
            break
        b, snr = dechirp(chunk, sf, bw, fs, is_downchirp=True)
        symbols.append(b)

    return symbols

# Load metadata
with open('shed_sdr_0930.sigmf-meta') as f:
    meta = json.load(f)

captures = meta['captures']
total_file_samples = 212977458 // 2  # ci8 = 2 bytes per sample

print(f"Total captures (bursts): {len(captures)}")

# Let's look at the first few bursts to understand the structure
print("\n=== Analyzing first burst ===")
burst_start = captures[0]['core:sample_start']
# Calculate burst length as gap to next burst (or reasonable estimate)
if len(captures) > 1:
    burst_len = captures[1]['core:sample_start'] - burst_start
else:
    burst_len = 82000

iq = load_burst('shed_sdr_0930.sigmf-data', burst_start, burst_len)
print(f"Burst length: {len(iq)} samples = {len(iq)/FS*1000:.1f} ms")
print(f"Max symbols possible: {len(iq) // N_samp}")

symbols = demod_burst(iq, SF, BW, FS)
print(f"Symbols: {symbols}")

# Try the first 10 bursts
print("\n=== First 10 bursts ===")
for b_idx in range(min(10, len(captures))):
    start = captures[b_idx]['core:sample_start']
    if b_idx + 1 < len(captures):
        blen = captures[b_idx + 1]['core:sample_start'] - start
    else:
        blen = total_file_samples - start
    
    iq = load_burst('shed_sdr_0930.sigmf-data', start, blen)
    syms = demod_burst(iq, SF, BW, FS)
    print(f"Burst {b_idx}: start={start}, syms={syms}")
