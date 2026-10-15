#!/usr/bin/env python3
"""
LoRa demodulator - Step 3: Full decode with proper alignment.
Now that we know the preamble structure, decode the payload.

LoRa packet structure:
  - 10 preamble upchirps (same bin)
  - 2 sync word symbols (bin = preamble_bin + sync_nibble * 8, mod N)
  - 2.25 SFD downchirps
  - Data symbols (SF7, CR4/5, implicit header)

For SF7 CR4/5 implicit mode:
  - Each symbol carries 7 raw bits
  - With CR4/5: 4 data bits + 1 parity bit per codeword
  - Actually: LoRa uses reduced rate for first 8 symbols (SF-2=5 bits)
  - Then full rate: SF=7 bits per symbol
"""

import numpy as np
import json
import struct
import sys

SF = 7
BW = 500000
FS = 1999999
N = 2**SF  # 128

T_sym = N / BW
N_samp = int(T_sym * FS)

def load_burst(data_file, sample_start, num_samples):
    offset = sample_start * 2
    with open(data_file, 'rb') as f:
        f.seek(offset)
        raw = f.read(num_samples * 2)
    iq = np.frombuffer(raw, dtype=np.int8).astype(np.float32)
    return iq[0::2] + 1j * iq[1::2]

def gen_chirp(sf, bw, fs, is_down=False):
    n = 2**sf
    t_sym = n / bw
    n_samp = int(t_sym * fs)
    t = np.arange(n_samp) / fs
    if is_down:
        phase = 2 * np.pi * (bw/2 * t - bw/(2*t_sym) * t**2)
    else:
        phase = 2 * np.pi * (-bw/2 * t + bw/(2*t_sym) * t**2)
    return np.exp(1j * phase)

down_chirp = gen_chirp(SF, BW, FS, is_down=True)
up_chirp = gen_chirp(SF, BW, FS, is_down=False)

def dechirp_at(iq, offset, use_downchirp=True):
    """Dechirp one symbol at given offset. Returns (bin, snr, magnitude_array)."""
    chunk = iq[offset:offset+N_samp]
    if len(chunk) < N_samp:
        return -1, 0, None
    ref = down_chirp if use_downchirp else up_chirp
    mixed = chunk * ref
    fft_result = np.fft.fft(mixed, n=N)
    magnitudes = np.abs(fft_result)
    peak_bin = int(np.argmax(magnitudes))
    snr = magnitudes[peak_bin] / (np.mean(magnitudes) + 1e-10)
    return peak_bin, snr, magnitudes

def fine_align_sfd(iq, preamble_end_offset):
    """
    After the sync word symbols, find the SFD (2.25 downchirps).
    The SFD consists of downchirps, which we detect by dechirping with an upchirp.
    """
    # Try different sub-sample offsets around the expected SFD position
    best_snr = 0
    best_offset = preamble_end_offset
    
    for delta in range(-N_samp, N_samp, N_samp // 8):
        off = preamble_end_offset + delta
        if off < 0 or off + N_samp > len(iq):
            continue
        b, snr, _ = dechirp_at(iq, off, use_downchirp=False)
        if snr > best_snr:
            best_snr = snr
            best_offset = off
    
    return best_offset

def decode_burst(iq):
    """
    Full decode of a burst:
    1. Find preamble
    2. Find sync word
    3. Find SFD
    4. Extract data symbols
    """
    max_syms = len(iq) // N_samp - 1
    
    # Step 1: Find preamble - look for consecutive high-SNR symbols with same bin
    bins = []
    snrs = []
    for i in range(max_syms):
        b, snr, _ = dechirp_at(iq, i * N_samp, use_downchirp=True)
        bins.append(b)
        snrs.append(snr)
    
    # Find start of preamble (first symbol with SNR > 10)
    preamble_start = -1
    for i in range(len(snrs)):
        if snrs[i] > 10:
            preamble_start = i
            break
    
    if preamble_start < 0:
        return None, None, "No preamble found"
    
    # The preamble should be 10 symbols
    # Find the preamble bin (most common high-SNR bin)
    preamble_bins = []
    for i in range(preamble_start, min(preamble_start + 15, len(bins))):
        if snrs[i] > 8:
            preamble_bins.append(bins[i])
        else:
            break
    
    if len(preamble_bins) < 5:
        return None, None, "Preamble too short"
    
    preamble_bin = max(set(preamble_bins), key=preamble_bins.count)
    preamble_len = len(preamble_bins)
    
    # After preamble, we expect:
    # - 2 sync word symbols (modified preamble bins)
    # - 2.25 SFD downchirps
    # The sync word 0x2C = 0b00101100 -> nibbles are 0x2 and 0xC
    # Sync word symbols: bin = preamble_bin + nibble * 8, mod N
    # So sync1 = (preamble_bin + 0x2 * 8) mod 128 = (preamble_bin + 16) mod 128
    # And sync2 = (preamble_bin + 0xC * 8) mod 128 = (preamble_bin + 96) mod 128
    
    sync_start = preamble_start + preamble_len
    
    # Verify sync word
    if sync_start + 2 < len(bins):
        sync1_expected = (preamble_bin + 2 * 8) % N
        sync2_expected = (preamble_bin + 0xC * 8) % N
        sync1_actual = bins[sync_start]
        sync2_actual = bins[sync_start + 1] if sync_start + 1 < len(bins) else -1
        
        # Check with tolerance
        sync1_ok = abs(sync1_actual - sync1_expected) <= 2 or abs(sync1_actual - sync1_expected) >= N - 2
        sync2_ok = abs(sync2_actual - sync2_expected) <= 2 or abs(sync2_actual - sync2_expected) >= N - 2
    else:
        sync1_ok = False
        sync2_ok = False
    
    # After sync word: 2.25 downchirps (SFD)
    # Total overhead before data: preamble(10) + sync(2) + SFD(2.25) = 14.25 symbols
    # Data starts at preamble_start + 14.25 symbols
    
    # But we need to find the exact alignment. Let's look for the SFD.
    # After sync word (2 symbols), there are 2.25 downchirps.
    # We can detect downchirps by dechirping with upchirp.
    
    sfd_start_sym = sync_start + 2
    
    # Verify SFD (downchirps should give high SNR when dechirped with upchirp)
    if sfd_start_sym < len(bins):
        sfd_b, sfd_snr, _ = dechirp_at(iq, sfd_start_sym * N_samp, use_downchirp=False)
    
    # Data starts after SFD (2.25 symbols after sync)
    # The 0.25 symbol is important for alignment
    data_start_sym = sfd_start_sym + 2  # The 0.25 is handled by fine alignment
    data_start_offset = int((preamble_start + 10 + 2 + 2.25) * N_samp)
    
    # Extract data symbols
    data_bins = []
    data_snrs = []
    sym_idx = 0
    while True:
        offset = data_start_offset + sym_idx * N_samp
        if offset + N_samp > len(iq):
            break
        b, snr, _ = dechirp_at(iq, offset, use_downchirp=True)
        data_bins.append(b)
        data_snrs.append(snr)
        sym_idx += 1
    
    # Subtract preamble bin to get raw values (deoffset)
    raw_symbols = [(b - preamble_bin) % N for b in data_bins]
    
    return raw_symbols, data_snrs, f"preamble={preamble_bin}, sync1_ok={sync1_ok}, sync2_ok={sync2_ok}, data_syms={len(data_bins)}"

# Load metadata
with open('shed_sdr_0930.sigmf-meta') as f:
    meta = json.load(f)
captures = meta['captures']
total_file_samples = 212977458 // 2

print(f"Total captures: {len(captures)}")

# Analyze first 20 bursts
for b_idx in range(min(20, len(captures))):
    start = captures[b_idx]['core:sample_start']
    if b_idx + 1 < len(captures):
        blen = captures[b_idx + 1]['core:sample_start'] - start
    else:
        blen = total_file_samples - start
    
    iq = load_burst('shed_sdr_0930.sigmf-data', start, blen)
    raw_syms, snrs, info = decode_burst(iq)
    
    print(f"\nBurst {b_idx}: {info}")
    if raw_syms is not None:
        # Show raw symbols and their SNR
        print(f"  Raw symbols (first 40): {raw_syms[:40]}")
        if snrs:
            # Filter out low-SNR symbols at the end
            valid_count = sum(1 for s in snrs if s > 5)
            print(f"  Valid symbols (SNR>5): {valid_count}, Total: {len(raw_syms)}")
            print(f"  Raw as hex: {' '.join(f'{s:02x}' for s in raw_syms[:40])}")
