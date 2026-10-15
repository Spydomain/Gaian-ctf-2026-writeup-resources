#!/usr/bin/env python3
"""
LoRa demodulator - Step 2: Proper preamble detection and alignment.
Analyze burst structure to understand the LoRa packet format.
"""

import numpy as np
import json

SF = 7
BW = 500000
FS = 1999999
N = 2**SF  # 128

T_sym = N / BW  # 0.000256 s
N_samp = int(T_sym * FS)  # samples per symbol at SDR rate
print(f"SF={SF}, BW={BW}, N={N}, T_sym={T_sym*1000:.4f}ms, N_samp={N_samp}")

def load_burst(data_file, sample_start, num_samples):
    offset = sample_start * 2
    with open(data_file, 'rb') as f:
        f.seek(offset)
        raw = f.read(num_samples * 2)
    iq = np.frombuffer(raw, dtype=np.int8).astype(np.float32)
    return iq[0::2] + 1j * iq[1::2]

def gen_chirp(sf, bw, fs, is_down=False):
    """Generate a reference chirp."""
    n = 2**sf
    t_sym = n / bw
    n_samp = int(t_sym * fs)
    t = np.arange(n_samp) / fs
    if is_down:
        phase = 2 * np.pi * (bw/2 * t - bw/(2*t_sym) * t**2)
    else:
        phase = 2 * np.pi * (-bw/2 * t + bw/(2*t_sym) * t**2)
    return np.exp(1j * phase)

# Reference chirps
down_chirp = gen_chirp(SF, BW, FS, is_down=True)  # conjugate of upchirp, for dechirping upchirps
up_chirp = gen_chirp(SF, BW, FS, is_down=False)    # conjugate of downchirp, for dechirping downchirps

def dechirp_at(iq, offset, use_downchirp=True):
    """Dechirp one symbol at given offset. Returns (bin, snr)."""
    chunk = iq[offset:offset+N_samp]
    if len(chunk) < N_samp:
        return -1, 0
    ref = down_chirp if use_downchirp else up_chirp
    mixed = chunk * ref
    fft_result = np.fft.fft(mixed, n=N)
    magnitudes = np.abs(fft_result)
    peak_bin = int(np.argmax(magnitudes))
    snr = magnitudes[peak_bin] / (np.mean(magnitudes) + 1e-10)
    return peak_bin, snr

def find_preamble_and_align(iq):
    """
    Find preamble: consecutive upchirps with the same bin value.
    Then find sync word symbols, then 2.25 downchirps (SFD).
    Returns offset of first data symbol.
    """
    max_syms = len(iq) // N_samp - 1
    
    # Step 1: Find a run of at least 6 identical bins (preamble upchirps)
    best_run_start = -1
    best_run_len = 0
    best_run_bin = -1
    
    run_start = 0
    run_bin = -1
    run_len = 0
    
    all_bins = []
    all_snrs = []
    
    for i in range(max_syms):
        b, snr = dechirp_at(iq, i * N_samp, use_downchirp=True)
        all_bins.append(b)
        all_snrs.append(snr)
        
        if abs(b - run_bin) <= 1 or abs(b - run_bin) == N-1:  # allow ±1 tolerance
            run_len += 1
        else:
            if run_len > best_run_len:
                best_run_len = run_len
                best_run_start = run_start
                best_run_bin = run_bin
            run_start = i
            run_bin = b
            run_len = 1
    
    if run_len > best_run_len:
        best_run_len = run_len
        best_run_start = run_start
        best_run_bin = run_bin
    
    return all_bins, all_snrs, best_run_start, best_run_len, best_run_bin

# Load metadata
with open('shed_sdr_0930.sigmf-meta') as f:
    meta = json.load(f)
captures = meta['captures']
total_file_samples = 212977458 // 2

print(f"Total captures: {len(captures)}")

# Analyze first 10 bursts in detail
for b_idx in range(min(15, len(captures))):
    start = captures[b_idx]['core:sample_start']
    if b_idx + 1 < len(captures):
        blen = captures[b_idx + 1]['core:sample_start'] - start
    else:
        blen = total_file_samples - start
    
    iq = load_burst('shed_sdr_0930.sigmf-data', start, blen)
    bins, snrs, pstart, plen, pbin = find_preamble_and_align(iq)
    
    print(f"\nBurst {b_idx}: start={start}, {len(iq)} samps, {len(bins)} syms")
    print(f"  Preamble: start_sym={pstart}, len={plen}, bin={pbin}")
    print(f"  All bins: {bins[:40]}...")
    print(f"  SNRs:     {[f'{s:.1f}' for s in snrs[:40]]}...")
