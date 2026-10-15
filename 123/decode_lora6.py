#!/usr/bin/env python3
"""
LoRa demodulator with fine timing alignment.

Based on analysis:
- Preamble: 10 upchirps
- Sync: 2 modified upchirps  
- SFD: 2.25 downchirps
- Data starts at preamble_start + 14.25 symbols from preamble start

The 0.25 symbol offset is crucial for proper data alignment.

After extracting raw symbol values (offset from preamble bin, mod 128):
  1. Gray decode
  2. Deinterleave  
  3. Hamming decode
  4. De-whiten (LoRa whitening sequence)
  5. Output bytes

For implicit mode with SF=7, CR=4/5:
  - First 8 symbols are "reduced rate": only SF-2=5 bits used, with CR=4/8
  - Remaining symbols: full SF=7 bits, CR=4/5
"""

import numpy as np
import json
import struct

SF = 7
BW = 500000
FS = 1999999
N = 2**SF  # 128
CR = 1  # 4/5
T_sym = N / BW
N_samp_float = T_sym * FS  # exact, not rounded
N_samp = int(N_samp_float)

print(f"SF={SF}, BW={BW}, N={N}, T_sym={T_sym*1e6:.1f}us, N_samp={N_samp} ({N_samp_float:.2f})")

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

def dechirp_symbol(iq, offset):
    """Dechirp a single symbol. Returns (bin, snr)."""
    chunk = iq[offset:offset+N_samp]
    if len(chunk) < N_samp:
        return -1, 0
    mixed = chunk * down_chirp
    fft_result = np.fft.fft(mixed, n=N)
    magnitudes = np.abs(fft_result)
    peak_bin = int(np.argmax(magnitudes))
    snr = magnitudes[peak_bin] / (np.mean(magnitudes) + 1e-10)
    return peak_bin, snr

def find_preamble_and_data(iq):
    """
    Find preamble, sync, SFD, and return data symbol values.
    Uses fine timing with the 0.25 symbol SFD offset.
    """
    max_syms = len(iq) // N_samp
    
    # Coarse search: find preamble
    bins = []
    snrs = []
    for i in range(max_syms):
        b, snr = dechirp_symbol(iq, i * N_samp)
        bins.append(b)
        snrs.append(snr)
    
    # Find first high-SNR symbol
    pstart = -1
    for i in range(len(snrs)):
        if snrs[i] > 10:
            pstart = i
            break
    if pstart < 0:
        return None, "No preamble"
    
    # Find preamble bin
    pbin = bins[pstart]
    pcount = 0
    for i in range(pstart, min(pstart + 15, len(bins))):
        diff = abs(bins[i] - pbin)
        if diff <= 2 or diff >= N - 2:
            pcount += 1
        else:
            break
    
    if pcount < 6:
        return None, f"Preamble too short: {pcount}"
    
    # Data starts at preamble_start + pcount + 2 (sync) + 2.25 (SFD) symbols
    # The 0.25 symbol offset is handled by shifting the data start by 0.25 * N_samp
    
    # Try to find best data start by maximizing SNR of first few data symbols
    best_start = None
    best_total_snr = 0
    
    # The data should start around preamble_start + pcount + 4.25 symbols
    nominal_start = int((pstart + pcount + 4.25) * N_samp_float)
    
    # Try offsets around the nominal start
    for delta in range(-N_samp, N_samp, N_samp // 16):
        test_start = nominal_start + delta
        if test_start < 0:
            continue
        
        total_snr = 0
        for k in range(min(5, (len(iq) - test_start) // N_samp)):
            b, snr = dechirp_symbol(iq, test_start + k * N_samp)
            total_snr += snr
        
        if total_snr > best_total_snr:
            best_total_snr = total_snr
            best_start = test_start
    
    if best_start is None:
        return None, "Could not find data start"
    
    # Extract data symbols
    data_bins = []
    idx = 0
    while True:
        offset = best_start + idx * N_samp
        if offset + N_samp > len(iq):
            break
        b, snr = dechirp_symbol(iq, offset)
        data_bins.append(b)
        idx += 1
    
    # Remove preamble offset to get raw values
    raw_symbols = [(b - pbin) % N for b in data_bins]
    
    return raw_symbols, f"pbin={pbin}, pcount={pcount}, nsyms={len(raw_symbols)}"

# LoRa whitening sequence (from the specification / common implementations)
# This is the standard LoRa whitening sequence
WHITENING_SEQ = [
    0xFF, 0xFE, 0xFC, 0xF8, 0xF0, 0xE1, 0xC2, 0x85, 0x0B, 0x17, 0x2F, 0x5E,
    0xBC, 0x78, 0xF1, 0xE3, 0xC6, 0x8D, 0x1A, 0x34, 0x68, 0xD0, 0xA0, 0x40,
    0x80, 0x01, 0x02, 0x04, 0x08, 0x11, 0x23, 0x47, 0x8E, 0x1C, 0x38, 0x71,
    0xE2, 0xC4, 0x89, 0x12, 0x25, 0x4B, 0x97, 0x2E, 0x5C, 0xB8, 0x70, 0xE0,
    0xC0, 0x81, 0x03, 0x06, 0x0C, 0x19, 0x32, 0x64, 0xC8, 0x90, 0x20, 0x41,
    0x82, 0x05, 0x0A, 0x15, 0x2B, 0x56, 0xAD, 0x5B, 0xB6, 0x6D, 0xDA, 0xB4,
    0x69, 0xD2, 0xA4, 0x48, 0x91, 0x22, 0x44, 0x88, 0x10, 0x21, 0x43, 0x86,
    0x0D, 0x1B, 0x36, 0x6C, 0xD8, 0xB0, 0x60, 0xC1, 0x83, 0x07, 0x0E, 0x1D,
    0x3A, 0x75, 0xEB, 0xD7, 0xAE, 0x5D, 0xBA, 0x74, 0xE8, 0xD1, 0xA2, 0x45,
    0x8B, 0x16, 0x2D, 0x5A, 0xB5, 0x6B, 0xD6, 0xAC, 0x59, 0xB2, 0x65, 0xCA,
    0x94, 0x28, 0x51, 0xA3, 0x46, 0x8C, 0x18, 0x31, 0x62, 0xC5, 0x8A, 0x14,
    0x29, 0x53, 0xA7, 0x4E, 0x9C, 0x39, 0x73, 0xE6, 0xCC, 0x98, 0x30, 0x61,
    0xC3, 0x87, 0x0F, 0x1E, 0x3C, 0x79, 0xF2, 0xE4, 0xC9, 0x92, 0x24, 0x49,
    0x93, 0x26, 0x4D, 0x9B, 0x37, 0x6E, 0xDC, 0xB9, 0x72, 0xE5, 0xCB, 0x96,
    0x2C, 0x58, 0xB1, 0x63, 0xC7, 0x8F, 0x1F, 0x3E, 0x7D, 0xFB, 0xF6, 0xEC,
    0xD9, 0xB3, 0x67, 0xCE, 0x9D, 0x3B, 0x77, 0xEE, 0xDD, 0xBB, 0x76, 0xED,
    0xDB, 0xB7, 0x6F, 0xDE, 0xBD, 0x7B, 0xF7, 0xEF, 0xDF, 0xBE, 0x7C, 0xF9,
    0xF3, 0xE7, 0xCF, 0x9E, 0x3D, 0x7A, 0xF5, 0xEA, 0xD5, 0xAA, 0x55, 0xAB,
    0x57, 0xAF, 0x5F, 0xBF, 0x7E, 0xFD, 0xFA, 0xF4, 0xE9, 0xD3, 0xA6, 0x4C,
    0x99, 0x33, 0x66, 0xCD, 0x9A, 0x35, 0x6A, 0xD4, 0xA8, 0x50, 0xA1, 0x42,
    0x84, 0x09, 0x13, 0x27, 0x4F, 0x9F, 0x3F, 0x7F, 0xFF, 0xFE, 0xFC, 0xF8,
    0xF0, 0xE1, 0xC2, 0x85
]

def gray_decode(n):
    mask = n >> 1
    while mask:
        n ^= mask
        mask >>= 1
    return n

def lora_decode_payload(raw_symbols, sf=7, cr=1, has_header=False):
    """
    Full LoRa payload decode from raw symbol values.
    
    For implicit mode (has_header=False):
    - First 8 symbols: reduced rate (SF-2=5 bits), CR=4/8
    - Remaining: full rate (SF=7 bits), CR=4/5
    """
    n = 2**sf
    
    # Step 1: Gray decode all symbols
    gray = [gray_decode(s) for s in raw_symbols]
    
    # Header symbols (first 8, reduced rate)
    header_sf = sf - 2  # 5 
    header_ppm = 8  # always 8 symbols for header block
    header_cr = 4  # CR 4/8
    
    # Mask to reduced rate bits
    header_syms = [s % (2**header_sf) for s in gray[:8]]
    data_syms = gray[8:]
    
    # Step 2: Deinterleave
    # LoRa interleaver: for block of PPM symbols, each SF bits wide,
    # produces SF codewords of PPM bits each
    
    def deinterleave_block(symbols, sf_bits, ppm):
        """
        Deinterleave one block.
        Input: ppm symbols, each sf_bits wide
        Output: sf_bits codewords, each ppm bits wide
        """
        codewords = []
        for j in range(sf_bits):
            cw = 0
            for i in range(ppm):
                bit_pos = (j - i) % sf_bits  # LoRa diagonal read
                bit = (symbols[i] >> bit_pos) & 1
                cw |= (bit << i)
            codewords.append(cw)
        return codewords
    
    # Header block: 8 symbols of 5 bits -> 5 codewords of 8 bits
    header_cws = deinterleave_block(header_syms, header_sf, header_ppm)
    
    # Data blocks: 5 symbols of 7 bits -> 7 codewords of 5 bits
    data_ppm = 4 + cr  # 5
    data_cws = []
    for i in range(0, len(data_syms) - data_ppm + 1, data_ppm):
        block = data_syms[i:i+data_ppm]
        cws = deinterleave_block(block, sf, data_ppm)
        data_cws.extend(cws)
    
    # Step 3: Hamming decode (extract 4 data bits from each codeword)
    header_nibbles = [cw & 0xF for cw in header_cws]
    data_nibbles = [cw & 0xF for cw in data_cws]
    
    all_nibbles = header_nibbles + data_nibbles
    
    # Step 4: Combine nibbles into bytes
    payload = []
    for i in range(0, len(all_nibbles) - 1, 2):
        byte = (all_nibbles[i] << 4) | all_nibbles[i + 1]
        payload.append(byte)
    
    # Step 5: Apply whitening
    dewhitened = []
    for i in range(len(payload)):
        if i < len(WHITENING_SEQ):
            dewhitened.append(payload[i] ^ WHITENING_SEQ[i])
        else:
            dewhitened.append(payload[i])
    
    return payload, dewhitened, all_nibbles

# Load metadata
with open('shed_sdr_0930.sigmf-meta') as f:
    meta = json.load(f)
captures = meta['captures']
total_file_samples = 212977458 // 2

print(f"Total captures: {len(captures)}")

# Decode first 20 bursts
for b_idx in range(min(25, len(captures))):
    start = captures[b_idx]['core:sample_start']
    if b_idx + 1 < len(captures):
        blen = captures[b_idx + 1]['core:sample_start'] - start
    else:
        blen = total_file_samples - start
    
    iq = load_burst('shed_sdr_0930.sigmf-data', start, blen)
    raw_syms, info = find_preamble_and_data(iq)
    
    if raw_syms is None:
        print(f"Burst {b_idx}: FAILED - {info}")
        continue
    
    payload, dewhitened, nibbles = lora_decode_payload(raw_syms, sf=SF, cr=CR, has_header=False)
    
    hex_raw = ' '.join(f'{b:02x}' for b in payload[:20])
    ascii_raw = ''.join(chr(b) if 32 <= b < 127 else '.' for b in payload[:20])
    hex_dew = ' '.join(f'{b:02x}' for b in dewhitened[:20])
    ascii_dew = ''.join(chr(b) if 32 <= b < 127 else '.' for b in dewhitened[:20])
    
    print(f"\nBurst {b_idx}: {info}")
    print(f"  Raw:       {hex_raw}")
    print(f"             {ascii_raw}")
    print(f"  Dewhiten:  {hex_dew}")
    print(f"             {ascii_dew}")

    # Also try without whitening but with different nibble ordering
    # Maybe nibbles are low-high instead of high-low
    payload_lh = []
    for i in range(0, len(nibbles) - 1, 2):
        byte = (nibbles[i+1] << 4) | nibbles[i]
        payload_lh.append(byte)
    hex_lh = ' '.join(f'{b:02x}' for b in payload_lh[:20])
    ascii_lh = ''.join(chr(b) if 32 <= b < 127 else '.' for b in payload_lh[:20])
    print(f"  Swap nib:  {hex_lh}")
    print(f"             {ascii_lh}")
