import json, numpy as np

SF=7; BW=500000; FS=1999999
N=2**SF; N_samp=int((N/BW)*FS)
meta=json.load(open('shed_sdr_0930.sigmf-meta'))
captures=meta['captures']


def load_burst(start,blen):
    offset=start*2
    with open('shed_sdr_0930.sigmf-data','rb') as f:
        f.seek(offset)
        raw=f.read(blen*2)
    iq=np.frombuffer(raw,dtype=np.int8).astype(np.float32)
    return iq[0::2]+1j*iq[1::2]


def demod_symbol(chunk):
    t_sym=N/BW
    t=np.arange(N_samp)/FS
    phase=2*np.pi*(-BW/2*t + BW/(2*t_sym)*t**2)
    ref=np.exp(1j*phase)
    mixed=chunk[:N_samp]*ref
    return int(np.argmax(np.abs(np.fft.fft(mixed,N))))


def gray_to_bin(g,b=7):
    v=g
    shift=1
    while shift<b:
        v ^= (g>>shift)
        shift <<=1
    return v


def sym_to_bytes(symbols):
    bits=[]
    for s in symbols:
        val=gray_to_bin(s)
        bits.extend([(val>>i)&1 for i in range(7)])
    payload=bytearray()
    for i in range(0,len(bits),8):
        byte=0
        for j in range(8):
            if i+j < len(bits):
                byte |= bits[i+j]<<j
        payload.append(byte)
    return payload

TOTAL=0
for i in range(len(captures)):
    start=captures[i]['core:sample_start']
    sb=captures[i+1]['core:sample_start'] if i+1 < len(captures) else None
    blen=sb-start if sb else 81959
    iq=load_burst(start,blen)
    syms=[demod_symbol(iq[j:j+N_samp]) for j in range(0,len(iq)-N_samp+1,N_samp) if len(iq[j:j+N_samp])==N_samp]
    bs=len(sym_to_bytes(syms))
    TOTAL+=bs
print('total bytes',TOTAL)
