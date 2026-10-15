#!/usr/bin/env python3
import numpy as np

LORA_WHITEN = [
    0xff,0xfe,0xfc,0xf8,0xf0,0xe1,0xc2,0x85,0x0b,0x17,0x2f,0x5e,0xbc,0x78,0xf1,0xe3,
    0xc6,0x8d,0x1a,0x34,0x68,0xd0,0xa0,0x40,0x80,0x01,0x02,0x04,0x08,0x11,0x23,0x47,
    0x8e,0x1c,0x38,0x71,0xe2,0xc4,0x89,0x12,0x25,0x4b,0x97,0x2e,0x5c,0xb8,0x70,0xe0,
    0xc0,0x81,0x03,0x06,0x0c,0x19,0x32,0x64,0xc9,0x92,0x24,0x49,0x93,0x26,0x4d,0x9b,
    0x37,0x6e,0xdc,0xb9,0x72,0xe4,0xc8,0x90,0x20,0x41,0x82,0x05,0x0a,0x15,0x2b,0x56,
    0xad,0x5b,0xb6,0x6d,0xda,0xb5,0x6b,0xd6,0xac,0x59,0xb2,0x65,0xcb,0x96,0x2c,0x58,
    0xb0,0x61,0xc3,0x87,0x0f,0x1f,0x3e,0x7d,0xfb,0xf6,0xed,0xdb,0xb7,0x6f,0xde,0xbd,
    0x7a,0xf5,0xeb,0xd7,0xae,0x5d,0xba,0x74,0xe8,0xd1,0xa2,0x44,0x88,0x10,0x21,0x43,
    0x86,0x0d,0x1b,0x36,0x6c,0xd8,0xb1,0x63,0xc7,0x8f,0x1e,0x3c,0x79,0xf3,0xe7,0xce,
    0x9c,0x39,0x73,0xe6,0xcc,0x98,0x31,0x62,0xc5,0x8b,0x16,0x2d,0x5a,0xb4,0x69,0xd2,
    0xa4,0x48,0x91,0x22,0x45,0x8a,0x14,0x29,0x52,0xa5,0x4a,0x95,0x2a,0x54,0xa9,0x53,
    0xa7,0x4e,0x9d,0x3b,0x77,0xee,0xdd,0xbb,0x76,0xec,0xd9,0xb3,0x67,0xcf,0x9e,0x3d,
    0x7b,0xf7,0xef,0xdf,0xbf,0x7e,0xfd,0xfa,0xf4,0xe9,0xd3,0xa6,0x4c,0x99,0x33,0x66,
    0xcd,0x9a,0x35,0x6a,0xd4,0xa8,0x51,0xa3,0x46,0x8c,0x18,0x30,0x60,0xc1,0x83,0x07,
    0x0e,0x1d,0x3a,0x75,0xea,0xd5,0xaa,0x55,0xab,0x57,0xaf,0x5f,0xbe,0x7c,0xf9,0xf2,
    0xe5,0xca,0x94,0x28,0x50,0xa1,0x42,0x84,0x09,0x13,0x27,0x4f,0x9f,0x3f,0x7f,0x00
]

def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def gray_bin2gray(s):
    return s ^ (s >> 1)

def gray_gray2bin(s):
    mask = s >> 1
    while mask:
        s ^= mask
        mask >>= 1
    return s

def decode_symbols(symbols, sf=7, cr=5, reverse_nibble=True, low_nibble_first=True):
    n_blocks = len(symbols) // cr
    nibbles = []
    for b in range(n_blocks):
        block = symbols[b*cr : (b+1)*cr]
        inter = np.zeros((cr, sf), dtype=np.uint8)
        for i in range(cr):
            v = int(block[i])
            for j in range(sf):
                inter[i, j] = (v >> (sf - 1 - j)) & 1
        deint = np.zeros((sf, cr), dtype=np.uint8)
        for i in range(cr):
            for j in range(sf):
                deint[(i - j - 1) % sf, i] = inter[i, j]
        for r in range(sf):
            cw = 0
            for j in range(cr):
                cw = (cw << 1) | int(deint[r, j])
            bits = [(cw >> (cr - 1 - k)) & 1 for k in range(cr)]
            d0, d1, d2, d3 = bits[0], bits[1], bits[2], bits[3]
            if reverse_nibble:
                nib = (d3 << 3) | (d2 << 2) | (d1 << 1) | d0
            else:
                nib = (d0 << 3) | (d1 << 2) | (d2 << 1) | d3
            nibbles.append(nib)
            
    bytes_out = []
    for i in range(0, len(nibbles) - 1, 2):
        if low_nibble_first:
            bytes_out.append((nibbles[i+1] << 4) | nibbles[i])
        else:
            bytes_out.append((nibbles[i] << 4) | nibbles[i+1])
    return bytes_out

FS = 1999999.0
BW = 500000.0
SF = 7
N = 128
T_sym = N / BW
N_samp_float = T_sym * FS

with open('shed_sdr_0930.sigmf-data', 'rb') as f:
    raw = f.read(81959 * 2)
iq = np.frombuffer(raw, dtype=np.int8).astype(np.float32)
iq = iq[0::2] + 1j * iq[1::2]

t = np.arange(512) / FS
phase_up = 2 * np.pi * (-BW/2 * t + (BW / (2 * T_sym)) * t**2)
upchirp = np.exp(1j * phase_up)
downchirp = np.conj(upchirp)

# We know preamble was at 8356. Data starts 14.25 symbols later = 8356 + 14.25*512 = 15652.
# Let's search around 15652 in steps of 1 sample (e.g. 15640 .. 15670)
for start_sample in range(15644, 15668):
    # Extract 115 symbols (23 blocks)
    raw_bins = []
    for k in range(115):
        pos = int(round(start_sample + k * N_samp_float))
        seg = iq[pos : pos + 512]
        prod = seg * downchirp
        f = np.abs(np.fft.fft(prod, n=512))
        raw_bins.append(np.argmax(f))
    
    # Try different bin-to-symbol conversions
    # In 512-point FFT, bin is 4 * symbol.
    # What if bin is rounded or divided by 4?
    for bin_shift in range(4):
        syms_base = [((b - bin_shift) // 4) % 128 for b in raw_bins]
        
        for gray_mode in ['bin2gray', 'gray2bin', 'none']:
            if gray_mode == 'bin2gray':
                syms = [gray_bin2gray(s) for s in syms_base]
            elif gray_mode == 'gray2bin':
                syms = [gray_gray2bin(s) for s in syms_base]
            else:
                syms = list(syms_base)
                
            for rev_nib in [True, False]:
                for lo_first in [True, False]:
                    dec_bytes = decode_symbols(syms, reverse_nibble=rev_nib, low_nibble_first=lo_first)
                    
                    for whiten in [True, False]:
                        if whiten:
                            final_bytes = [b ^ LORA_WHITEN[i] for i, b in enumerate(dec_bytes)]
                        else:
                            final_bytes = dec_bytes
                            
                        # Check if first 3 bytes look like Dealer mark + 'M'
                        # E.g. two uppercase ASCII letters + 'M'
                        b0, b1, b2 = final_bytes[0], final_bytes[1], final_bytes[2]
                        if 65 <= b0 <= 90 and 65 <= b1 <= 90 and b2 == ord('M'):
                            hdr = ''.join(chr(x) for x in final_bytes[:3])
                            print(f"MATCH! start={start_sample}, bin_shift={bin_shift}, gray={gray_mode}, rev={rev_nib}, lo={lo_first}, whiten={whiten}")
                            print(f"  Header: {hdr} ({final_bytes[:10]})")
                            # Check CRC
                            for plen in range(10, len(final_bytes)):
                                pdata = final_bytes[:plen-2]
                                pcrc = (final_bytes[plen-2] << 8) | final_bytes[plen-1]
                                if crc16(pdata) == pcrc:
                                    print(f"  CRC MATCH! Length = {plen}, CRC = {hex(pcrc)}")
                                    print(f"  Payload: {bytes(final_bytes[:plen])}")
