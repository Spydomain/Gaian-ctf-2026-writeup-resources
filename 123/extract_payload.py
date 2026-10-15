#!/usr/bin/env python3
import json, numpy as np, sys

# LoRa parameters
SF = 7
BW = 500000
FS = 1999999
N = 2**SF
N_samp = int((N/BW)*FS)

# Load metadata
meta = json.load(open('shed_sdr_0930.sigmf-meta'))
captures = meta['captures']

# Load burst function

def load_burst(sample_start, num_samples):
    offset = sample_start * 2
    with open('shed_sdr_0930.sigmf-data', 'rb') as f:
        f.seek(offset)
        raw = f.read(num_samples*2)
    iq = np.frombuffer(raw, dtype=np.int8).astype(np.float32)
    return iq[0::2] + 1j * iq[1::2]

# Demodulate one symbol

def demod_symbol(chunk):
    t_sym = N / BW
    t = np.arange(N_samp)/FS
    phase = 2*np.pi*(-BW/2*t + BW/(2*t_sym)*t**2)
    ref_chirp = np.exp(1j*phase)
    mixed = chunk[:N_samp] * ref_chirp
    fft = np.fft.fft(mixed, n=N)
    peak = int(np.argmax(np.abs(fft)))
    return peak

# Convert symbols to bytes

def symbols_to_bytes(syms):
    bits=[]
    for s in syms:
        val = int(s)
        bits.extend([(val>>i)&1 for i in range(7)])
    payload=bytearray()
    for i in range(0,len(bits),8):
        byte=0
        for j in range(8):
            if i+j < len(bits):
                byte |= bits[i+j]<<j
        payload.append(byte)
    return payload

# Get packet size per burst
burst_start = captures[0]['core:sample_start']
blen = captures[1]['core:sample_start']-burst_start if len(captures)>1 else 81959

# iterate over first 4 bursts
for idx in range(4):
    start = captures[idx]['core:sample_start']
    blen = (captures[idx+1]['core:sample_start']-start) if idx+1 < len(captures) else 81959
    iq = load_burst(start, blen)
    syms = []
    for i in range(0,len(iq)-N_samp+1,N_samp):
        chunk = iq[i:i+N_samp]
        if len(chunk)<N_samp: break
        syms.append(demod_symbol(chunk))
    payload = symbols_to_bytes(syms)
    print(f"Burst {idx} payload (len {len(payload)}):", payload.hex()[:50])
