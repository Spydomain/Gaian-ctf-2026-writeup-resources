#!/usr/bin/env python3
"""
LoRa demodulator - trying to match the well-known gr-lora implementation.

Key references:
- https://github.com/rpp0/gr-lora (Matt Knight's implementation)
- https://github.com/tapparelj/gr-lora_sdr (Tapparel's implementation)

LoRa PHY for SF7, BW=500kHz, CR=4/5, implicit header:

The dechirped symbol values go through:
1. Gray demapping: val = val XOR (val >> 1)  -- this is incorrect for LoRa
   Actually LoRa uses: val = gray_decode(val) -- standard gray to binary

2. The first 8 symbols use reduced rate (SF-2 bits only, CR=4/8)
   They carry the PHY header (in explicit mode) or start of payload (in implicit mode)

3. For data symbols after the first 8: full SF bits, CR as configured

4. Deinterleave: reads diagonal from an (SF x (4+CR)) matrix for data blocks
   For header: (SF-2) x 8 matrix

5. Hamming decode: extract 4 data bits from (4+CR) bit codewords

6. Whitening: XOR with a sequence (LoRa uses a specific whitening sequence)

7. CRC check (optional)

Let me try without FEC first -- just extract the raw bits and see if the
data makes sense as a direct byte stream (since the frame structure has its
own CRC, maybe the data is simpler than I think).

Actually, let me take an entirely different approach. The key observation is:
- Each burst contains one LoRa packet  
- SF=7 means each symbol carries 7 bits
- With CR=4/5, we need 5 symbols per 4*7/5 = ... no wait

Actually let me re-think. In LoRa:
- Each symbol value is in range [0, 2^SF - 1] = [0, 127]
- After gray decoding, still 7 bits per symbol
- These 7 bits are split across codewords via interleaving
- Each codeword has 4+CR bits (5 for CR=4/5)
- After Hamming decoding, each codeword gives 4 data bits

So: SF=7 symbols per interleave block, producing (4+CR)=5 codewords,
each giving 4 data nibbles.

Wait - that's the interleave structure:
- One interleave block = (4+CR) symbols = 5 symbols
- Each symbol has SF=7 bits
- The interleaver reads SF codewords of (4+CR) bits each
- So 5 symbols of 7 bits -> 7 codewords of 5 bits -> 7 nibbles of 4 bits

For the header (first 8 symbols, reduced rate):
- 8 symbols of (SF-2)=5 bits -> 5 codewords of 8 bits -> 5 nibbles of 4 bits

Hmm, this doesn't add up. Let me re-read the spec more carefully.

Actually, the LoRa interleaver works as:
- For each block of (4+CR) symbols:
  - Each symbol carries SF bits
  - Write symbols as rows of an SF x (4+CR) matrix
  - Read diagonally to produce SF codewords of (4+CR) bits each
  - Hamming decode each codeword: (4+CR) -> 4 data bits
  - So each block of (4+CR) symbols produces SF nibbles = SF*4 data bits

For SF=7, CR=1 (4/5):
  - Block of 5 symbols -> 7 codewords of 5 bits -> 7 nibbles -> 3.5 bytes

For header (8 symbols, SF-2=5 bits, CR=4):
  - Block of 8 symbols -> 5 codewords of 8 bits -> 5 nibbles -> 2.5 bytes

Let me try yet another approach: skip the full FEC decode and look for the
raw data pattern. The manual says the data is just pixel values (unsigned 8-bit),
and the frame has a CRC-16 at the end. Maybe I can figure out the correct 
decoding by trial and error with known patterns.
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
N_samp = int(T_sym * FS)

print(f"SF={SF}, BW={BW}, N={N}, T_sym={T_sym*1000:.4f}ms, N_samp={N_samp}")

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

def dechirp_at(iq, offset):
    chunk = iq[offset:offset+N_samp]
    if len(chunk) < N_samp:
        return -1, 0
    mixed = chunk * down_chirp
    fft_result = np.fft.fft(mixed, n=N)
    magnitudes = np.abs(fft_result)
    peak_bin = int(np.argmax(magnitudes))
    snr = magnitudes[peak_bin] / (np.mean(magnitudes) + 1e-10)
    return peak_bin, snr

def find_preamble(iq):
    """Find preamble and return (preamble_bin, data_start_sample)."""
    max_syms = len(iq) // N_samp
    bins = []
    snrs = []
    for i in range(max_syms):
        b, snr = dechirp_at(iq, i * N_samp)
        bins.append(b)
        snrs.append(snr)
    
    # Find start of high-SNR region
    pstart = -1
    for i in range(len(snrs)):
        if snrs[i] > 10:
            pstart = i
            break
    if pstart < 0:
        return None, None, bins, snrs
    
    # Find preamble bin (most common value in high-SNR region)
    pbin = bins[pstart]
    pcount = 0
    for i in range(pstart, min(pstart + 15, len(bins))):
        if abs(bins[i] - pbin) <= 2 or abs(bins[i] - pbin) >= N - 2:
            pcount += 1
        else:
            break
    
    return pbin, pstart, bins, snrs

# Load metadata
with open('shed_sdr_0930.sigmf-meta') as f:
    meta = json.load(f)
captures = meta['captures']
total_file_samples = 212977458 // 2

# Now let me look more carefully at the structure AFTER the preamble
# to understand the sync word, SFD, and where data actually starts

print("=== Detailed analysis of burst structure ===\n")

for b_idx in [1, 2, 4, 5, 10]:  # Pick a few diverse bursts
    start = captures[b_idx]['core:sample_start']
    if b_idx + 1 < len(captures):
        blen = captures[b_idx + 1]['core:sample_start'] - start
    else:
        blen = total_file_samples - start
    
    iq = load_burst('shed_sdr_0930.sigmf-data', start, blen)
    pbin, pstart, bins, snrs = find_preamble(iq)
    
    if pbin is None:
        print(f"Burst {b_idx}: No preamble found")
        continue
    
    # Count preamble
    pcount = 0
    for i in range(pstart, min(pstart + 15, len(bins))):
        if abs(bins[i] - pbin) <= 2 or abs(bins[i] - pbin) >= N - 2:
            pcount += 1
        else:
            break
    
    print(f"Burst {b_idx}: preamble_bin={pbin}, start={pstart}, count={pcount}")
    
    # Show symbols after preamble with their raw values and offsets from preamble_bin
    print(f"  Symbols around preamble end (offset from pbin):")
    for i in range(max(0, pstart+pcount-2), min(pstart+pcount+20, len(bins))):
        offset_val = (bins[i] - pbin) % N
        label = ""
        if i < pstart + pcount:
            label = " [preamble]"
        elif i < pstart + pcount + 2:
            label = " [sync?]"
        elif i < pstart + pcount + 5:
            label = " [SFD?]"
        else:
            label = " [data]"
        
        # Also check if this is a downchirp by dechirping with upchirp
        up_chirp_ref = gen_chirp(SF, BW, FS, is_down=False)
        chunk = iq[i*N_samp:(i+1)*N_samp]
        if len(chunk) >= N_samp:
            mixed_down = chunk * up_chirp_ref
            fft_down = np.abs(np.fft.fft(mixed_down, n=N))
            down_peak = int(np.argmax(fft_down))
            down_snr = fft_down[down_peak] / (np.mean(fft_down) + 1e-10)
        else:
            down_peak = -1
            down_snr = 0
        
        print(f"    sym[{i:3d}]: bin={bins[i]:4d}, offset={offset_val:4d}, "
              f"SNR={snrs[i]:6.1f}, downchirp_SNR={down_snr:6.1f}{label}")
    print()
