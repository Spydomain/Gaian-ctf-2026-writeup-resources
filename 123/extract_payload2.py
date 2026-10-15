#!/usr/bin/env python3
import json, numpy as np, sys

# LoRa parameters
SF = 7
BW = 500000
FS = 1999999
N = 2**SF
N_samp = int((N/BW)*FS)

def gray_to_bin(g, bits=7):
    b = g
    shift = 1
    while shift < bits:
        b ^= (g >> shift)
        shift <<=1
    return b

meta = json.load(open('shed_sdr_0930.sigmf-meta'))
captures = meta['captures']


def load_burst(sample_start, num_samples):
    offset=sample_start*2
    with open('shed_sdr_0930.sigmf-data','rb') as f:
        f.seek(offset)
        raw=f.read(num_samples*2)
    iq=np.frombuffer(raw,dtype=np.int8).astype(np.float32)
    return iq[0::2]+1j*iq[1::2]

def demod_symbol(chunk):
    t_sym=N/BW
    t=np.arange(N_samp)/FS
    phase=2*np.pi*(-BW/2*t + BW/(2*t_sym)*t**2)
    ref_chirp=np.exp(1j*phase)
    mixed=chunk[:N_samp]*ref_chirp
    return int(np.argmax(np.abs(np.fft.fft(mixed,N))))

# convert symbols to payload bytes: first convert gray to binary, then bits LSB-first

def symbols_to_bytes(symbols, bits_per_sym=7):
    bits=[]
    for s in symbols:
        val=gray_to_bin(s,bits_per_sym)
        bits.extend([(val>>i)&1 for i in range(bits_per_sym)])
    payload=bytearray()
    for i in range(0,len(bits),8):
        byte=0
        for j in range(8):
            if i+j < len(bits):
                byte |= bits[i+j]<<j
        payload.append(byte)
    return payload

# Test first few bursts
for i in range(5):
    start=captures[i]['core:sample_start']
    sb=captures[i+1]['core:sample_start'] if i+1 < len(captures) else 81959
    blen=sb-start if sb else 81959
    iq=load_burst(start,blen)
    syms=[demod_symbol(iq[j:j+N_samp]) for j in range(0,len(iq)-N_samp+1,N_samp) if len(iq[j:j+N_samp])==N_samp]
    payload=symbols_to_bytes(syms)
    print(i, len(payload), payload[:40].hex())
