#!/usr/bin/env python3
"""
LoRa demodulator - Full implementation.

Key LoRa PHY steps (after dechirping to get raw bin values):
1. Gray demapping: bin XOR (bin >> 1)  -- actually for LoRa it's just a standard gray decode
2. Deinterleaving: symbols are interleaved across SF bits
3. Hamming FEC decoding (CR 4/5 = 1 parity bit)
4. CRC check (optional, in our case radio CRC is off but frame CRC exists)

For SF7, implicit mode, CR 4/5:
- First 8 symbols use reduced rate: SF-2=5 bits per symbol, CR=4/8 (always)
- Remaining symbols: SF=7 bits per symbol, CR=4/5

Actually, let me step back. The key insight is that the raw dechirped bins
already represent the data before interleaving. In LoRa:
- Dechirp -> get bin value (0 to 2^SF - 1)
- The bin values are the "symbols"
- Gray decode each symbol
- Then deinterleave and Hamming decode

But actually, given the complexity of implementing full LoRa decoding,
let me try a different approach: use the fact that I can see consistent
patterns in the raw symbols. Maybe I should try to work with existing
tools or implement a simpler direct approach.

Let me first check if the frame structure matches what the manual describes:
- Two-letter dealer mark + frame type 'M' + layer number + line number + data + CRC-16

If the payload is directly the symbol values (without FEC), the consistent
first bytes would be the dealer mark.
"""

import numpy as np
import json

SF = 7
BW = 500000
FS = 1999999
N = 2**SF  # 128
CR = 1  # Coding rate 4/5
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
    chunk = iq[offset:offset+N_samp]
    if len(chunk) < N_samp:
        return -1, 0
    ref = down_chirp if use_downchirp else up_chirp
    mixed = chunk * ref
    # Use zero-padded FFT for better resolution
    fft_result = np.fft.fft(mixed, n=N)
    magnitudes = np.abs(fft_result)
    peak_bin = int(np.argmax(magnitudes))
    snr = magnitudes[peak_bin] / (np.mean(magnitudes) + 1e-10)
    return peak_bin, snr

def gray_decode(n):
    """Standard gray to binary decode."""
    mask = n >> 1
    while mask:
        n ^= mask
        mask >>= 1
    return n

def gray_encode(n):
    """Binary to gray encode."""
    return n ^ (n >> 1)

def find_and_decode_burst(iq):
    """
    Find preamble, sync word, SFD, then extract and decode data symbols.
    """
    max_syms = len(iq) // N_samp
    
    # Dechirp all symbols
    all_bins = []
    all_snrs = []
    for i in range(max_syms):
        b, snr = dechirp_at(iq, i * N_samp, use_downchirp=True)
        all_bins.append(b)
        all_snrs.append(snr)
    
    # Find preamble start (first high-SNR symbol)
    preamble_start = -1
    for i in range(len(all_snrs)):
        if all_snrs[i] > 10:
            preamble_start = i
            break
    
    if preamble_start < 0:
        return None, "No preamble"
    
    # Find preamble bin (10 consecutive same-value symbols)
    preamble_bin = all_bins[preamble_start]
    preamble_count = 0
    for i in range(preamble_start, min(preamble_start + 15, len(all_bins))):
        if abs(all_bins[i] - preamble_bin) <= 2 or abs(all_bins[i] - preamble_bin) >= N - 2:
            preamble_count += 1
        else:
            break
    
    # After preamble: 2 sync word symbols, then 2.25 SFD downchirps
    # Data starts at preamble_start + preamble_count + 2 + 2.25
    # But the 0.25 is tricky. Let's try different offsets.
    
    # The standard LoRa structure after preamble:
    # sync_word_sym1, sync_word_sym2, 2.25 downchirps, data...
    # Total: preamble_count + 2 + 2.25 = preamble_count + 4.25 symbols offset
    
    # Let me try scanning for the first data symbols after the preamble+sync+SFD
    # by looking for where the SNR stays high but the bins stop repeating
    
    # First, identify the sync and SFD region
    sync_start = preamble_start + preamble_count
    
    # Verify sync word (0x2C):
    # sync1 = (preamble_bin + (sync_word >> 4) * (N/16)) % N
    # For LoRa, sync word nibbles scale by N/16 = 128/16 = 8
    # 0x2C -> high nibble 0x2, low nibble 0xC
    # But wait - different implementations use different formulas.
    # Let me just check what the sync symbols are.
    
    if sync_start + 1 < len(all_bins):
        sync1 = all_bins[sync_start]
        sync2 = all_bins[sync_start + 1]
        sync1_offset = (sync1 - preamble_bin) % N
        sync2_offset = (sync2 - preamble_bin) % N
        
        # For sync word 0x2C, with N=128:
        # Standard: sync1_offset = (sync_word & 0xF0) >> 4 * 8 = 2*8 = 16
        #           sync2_offset = (sync_word & 0x0F) * 8 = 12*8 = 96
        # But it could also be that the high nibble goes to sync2.
        
        # Actually, looking at the data:
        # Burst 4: preamble_bin=14, sync1=18(+4), sync2=6(-8) -> offsets 4, -8 (or 120)
        # Burst 5: preamble_bin=15, sync1=18(+3), sync2=6(-9)
        # These don't match 0x2C = {2,C}*8 = {16,96}
        
        # Let me check what the actual offsets are...
        pass
    
    # Let me try to find the data start by looking at where the downchirps are
    # Downchirps will show up when dechirped with upchirp
    for test_offset in range(sync_start, min(sync_start + 8, len(all_bins))):
        b_down, snr_down = dechirp_at(iq, test_offset * N_samp, use_downchirp=False)
        b_up, snr_up = dechirp_at(iq, test_offset * N_samp, use_downchirp=True)
        pass  # We'll check this manually

    # Try data extraction starting at various offsets after preamble
    # The standard is: preamble(N) + sync(2) + SFD(2.25) = N+4.25
    # With our integer symbol boundaries, let's try preamble_count + 4 and + 5
    
    best_data = None
    best_score = 0
    
    for data_offset_syms in [4, 5]:  # Try both
        data_start = preamble_start + preamble_count + data_offset_syms
        
        # Also try sub-symbol alignment with 0.25 symbol offset
        for quarter in [0, 0.25, 0.5, 0.75]:
            data_start_samp = int((preamble_start + preamble_count + data_offset_syms + quarter) * N_samp)
            
            data_bins = []
            idx = 0
            while True:
                offset = data_start_samp + idx * N_samp
                if offset + N_samp > len(iq):
                    break
                b, snr = dechirp_at(iq, offset, use_downchirp=True)
                if snr < 3:
                    break
                data_bins.append(b)
                idx += 1
            
            if len(data_bins) > best_score:
                best_score = len(data_bins)
                best_data = data_bins
    
    if best_data is None:
        return None, "No data found"
    
    # Remove preamble offset
    raw_symbols = [(b - preamble_bin) % N for b in best_data]
    
    return raw_symbols, f"preamble_bin={preamble_bin}, data_syms={len(raw_symbols)}"


# Now let's do the LoRa FEC decoding
# SF7, CR4/5, implicit mode
# 
# Step 1: Gray decode each symbol
# Step 2: Deinterleave
# Step 3: Hamming decode
# Step 4: Pack into bytes
#
# For implicit mode, the first block (8 symbols) always uses:
#   - Reduced rate: SF-2 = 5 bits per symbol
#   - CR 4/8 (maximum redundancy)
# After that: SF = 7 bits per symbol, CR 4/5
#
# Interleaving is done in blocks of (4+CR) symbols = 5 symbols for CR4/5 (or 8 for header)

def lora_decode_symbols(raw_symbols, sf=7, cr=1):
    """
    Decode LoRa symbols to bytes.
    
    For implicit mode:
    - First 8 symbols: reduced rate (sf-2 bits), CR=4/8
    - Remaining: full rate (sf bits), CR=4/cr (cr=1 for 4/5)
    
    Steps: gray decode -> deinterleave -> hamming decode -> nibble combine
    """
    
    # Header block (8 symbols, reduced rate)
    header_sf = sf - 2  # 5
    header_cr = 4  # 4/8 
    header_ppm = 4 + header_cr  # 8
    
    # Data blocks (groups of 4+cr symbols)
    data_ppm = 4 + cr  # 5
    data_sf = sf  # 7
    
    # Step 1: Gray decode
    gray_decoded = [gray_decode(s) for s in raw_symbols]
    
    # For the header (first 8 symbols), we only use the lower (sf-2) bits
    header_symbols = [s % (2**header_sf) for s in gray_decoded[:8]]
    data_symbols = gray_decoded[8:]
    
    # Step 2: Deinterleave header (8 symbols, 5 bits each -> produces header_sf codewords of 8 bits)
    # Actually, deinterleaving produces codewords.
    # For header: 8 symbols of 5 bits -> 5 codewords of 8 bits
    # For data: ppm symbols of sf bits -> sf codewords of ppm bits
    
    def deinterleave(symbols, sf_bits, ppm):
        """
        LoRa deinterleaver.
        Takes ppm symbols, each sf_bits wide.
        Produces sf_bits codewords, each ppm bits wide.
        
        The interleaver is a simple diagonal read/write of a ppm x sf_bits matrix.
        """
        codewords = []
        for j in range(sf_bits):
            cw = 0
            for i in range(ppm):
                # Extract bit j from symbol i, cyclically rotated
                bit = (symbols[i] >> ((j + i) % sf_bits)) & 1
                cw |= (bit << i)
            codewords.append(cw)
        return codewords
    
    # Process header
    header_codewords = deinterleave(header_symbols, header_sf, header_ppm)
    
    # Step 3: Hamming decode
    # For CR 4/8: 8-bit codewords -> 4 data bits (each codeword gives one nibble)
    # For CR 4/5: 5-bit codewords -> 4 data bits (parity check)
    
    def hamming_decode_cr48(cw):
        """Decode 8-bit Hamming codeword to 4 data bits."""
        # For CR 4/8 (Hamming(8,4)): bits are d0,d1,d2,d3,p0,p1,p2,p3
        # Just extract the 4 data bits (simplified)
        return cw & 0xF
    
    def hamming_decode_cr45(cw):
        """Decode 5-bit codeword (4 data + 1 parity) to 4 data bits."""
        return cw & 0xF
    
    # Decode header nibbles
    header_nibbles = [hamming_decode_cr48(cw) for cw in header_codewords]
    
    # Process data symbols in blocks of ppm (5)
    data_nibbles = []
    for block_start in range(0, len(data_symbols) - data_ppm + 1, data_ppm):
        block = data_symbols[block_start:block_start + data_ppm]
        if len(block) < data_ppm:
            break
        codewords = deinterleave(block, data_sf, data_ppm)
        nibbles = [hamming_decode_cr45(cw) for cw in codewords]
        data_nibbles.extend(nibbles)
    
    # Combine nibbles into bytes (two nibbles per byte)
    all_nibbles = header_nibbles + data_nibbles
    payload_bytes = []
    for i in range(0, len(all_nibbles) - 1, 2):
        byte = (all_nibbles[i] << 4) | all_nibbles[i + 1]
        payload_bytes.append(byte)
    
    return payload_bytes, all_nibbles

# Load metadata
with open('shed_sdr_0930.sigmf-meta') as f:
    meta = json.load(f)
captures = meta['captures']
total_file_samples = 212977458 // 2

print(f"Total captures: {len(captures)}")

# Decode first 20 bursts
for b_idx in range(min(20, len(captures))):
    start = captures[b_idx]['core:sample_start']
    if b_idx + 1 < len(captures):
        blen = captures[b_idx + 1]['core:sample_start'] - start
    else:
        blen = total_file_samples - start
    
    iq = load_burst('shed_sdr_0930.sigmf-data', start, blen)
    raw_syms, info = find_and_decode_burst(iq)
    
    if raw_syms is None:
        print(f"\nBurst {b_idx}: FAILED - {info}")
        continue
    
    # Try decoding to bytes
    payload_bytes, nibbles = lora_decode_symbols(raw_syms, sf=SF, cr=CR)
    
    # Show results
    hex_str = ' '.join(f'{b:02x}' for b in payload_bytes[:30])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in payload_bytes[:30])
    
    print(f"\nBurst {b_idx}: {info}")
    print(f"  Raw syms (first 20): {raw_syms[:20]}")
    print(f"  Payload hex: {hex_str}")
    print(f"  Payload ASCII: {ascii_str}")
