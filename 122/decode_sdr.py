import json
import numpy as np

ROOT = __import__('pathlib').Path(__file__).resolve().parent
META = json.loads((ROOT / 'coop_sdr_0655.sigmf-meta').read_text())
STARTS = [c['core:sample_start'] for c in META['captures']]
IQ = np.memmap(ROOT / 'coop_sdr_0655.sigmf-data', dtype=np.int8, mode='r').reshape(-1, 2)
N = 512
FS = 1_999_999
BW = 500_000
t = np.arange(N) / FS
CHIRP = np.exp(2j * np.pi * (-BW / 2 * t + BW / (2 * (N / FS)) * t * t))


def symbols(start, count):
    data = IQ[start:start + count * N]
    if len(data) != count * N:
        raise ValueError('short capture')
    z = data.astype(np.float32)
    z = (z[:, 0] + 1j * z[:, 1]).reshape(count, N)
    spec = abs(np.fft.fft(z * CHIRP.conj(), axis=1))
    return np.argmax(spec, axis=1) % 128, spec.max(axis=1)


def fine_symbols(start, count):
    data = IQ[start:start + count * N]
    if len(data) != count * N:
        raise ValueError('short capture')
    z = data.astype(np.float32)
    z = (z[:, 0] + 1j * z[:, 1]).reshape(count, N)
    spec = abs(np.fft.fft(z * CHIRP.conj(), n=2048, axis=1))
    return np.argmax(spec, axis=1) / 4, spec.max(axis=1)


def gray(syms, header=False):
    dec = [(int(s) - 1) % 128 for s in syms]
    if header:
        dec = [s // 4 for s in dec]
    return [s ^ (s >> 1) for s in dec]


def deinterleave(syms, sf):
    n = len(syms)
    return [sum(((syms[m] >> ((k - m) % sf)) & 1) << m for m in range(n)) for k in range(sf)]


def header(syms):
    cw = deinterleave(gray(syms, True), 5)
    ns = [x & 15 for x in cw]
    length = ns[0] * 16 + ns[1]
    cr = ns[2] >> 1
    crc = bool(ns[2] & 1)
    b = [((ns[i] >> j) & 1) for i in range(3) for j in (3, 2, 1, 0)]
    mat = [
        (1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0),
        (1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1),
        (0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0),
        (0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1),
        (0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1),
    ]
    chk = sum((sum(x * y for x, y in zip(row, b)) % 2) << (4 - i) for i, row in enumerate(mat))
    valid = (ns[3] == (chk >> 4) and ns[4] == (chk & 15) and 1 <= cr <= 4)
    return length, cr, crc, valid, ns


def dewhiten(data):
    reg = 255
    out = bytearray()
    for byte in data:
        out.append(byte ^ reg)
        fb = ((reg >> 7) ^ (reg >> 5) ^ (reg >> 4) ^ (reg >> 3)) & 1
        reg = (reg * 2 + fb) & 255
    return bytes(out)


def demod_capture(index):
    cap = STARTS[index]
    end = STARTS[index + 1] if index + 1 < len(STARTS) else len(IQ)
    # The squelch saves several milliseconds of silence before the preamble.
    raw = IQ[cap: min(cap + 12000, end)].astype(np.float32)
    power = raw[:, 0] ** 2 + raw[:, 1] ** 2
    blocks = np.array([power[j:j + 64].mean() for j in range(0, len(power) - 64, 64)])
    active = np.flatnonzero(blocks > 0.8)
    if not len(active):
        return None
    rough = cap + int(active[0] * 64) + 256
    base = int(symbols(rough, 1)[0][0])
    signed = ((base + 64) % 128) - 64
    start = rough - 4 * signed
    pre, amps = symbols(start, 16)
    base = int(np.bincount(pre[1:9], minlength=128).argmax())
    sync = next((j for j in range(5, 13)
                 if (int(pre[j]) - base) % 128 == 8
                 and (int(pre[j + 1]) - base) % 128 == 16), None)
    fine_pre, _ = fine_symbols(start + N, 6)
    base_fine = float(np.median(fine_pre))
    candidates = [sync] if sync is not None else list(range(5, 12))
    valid = False
    for candidate in candidates:
        for correction in (0, -4, 4, -8, 8):
            data_start = start + (candidate + 4) * N + N // 4 + correction
            hs, _ = fine_symbols(data_start, 8)
            hs = np.rint((hs - base_fine) % 128).astype(int) % 128
            length, cr, has_crc, valid, ns = header(hs)
            if valid:
                sync = candidate
                break
        if valid:
            break
    if not valid:
        return {'error': 'header', 'start': cap, 'header': hs.tolist(), 'nibbles': ns}
    total_bytes = length + (2 if has_crc else 0)
    payload_count = ((total_bytes * 2 + 6) // 7) * (cr + 4)
    nsyms = 8 + payload_count
    if data_start + nsyms * N > end + 2000:
        return {'error': 'long', 'start': cap, 'length': length, 'count': nsyms, 'available': (end - data_start) // N}
    syms, levels = fine_symbols(data_start, nsyms)
    syms = np.rint((syms - base_fine) % 128).astype(int) % 128
    codewords = []
    decoded = gray(syms[8:])
    for j in range(0, len(decoded), cr + 4):
        codewords.extend(deinterleave(decoded[j:j + cr + 4], 7))
    nibbles = [x & 15 for x in codewords]
    coded = bytes(nibbles[j] | (nibbles[j + 1] << 4) for j in range(0, total_bytes * 2, 2))
    payload = dewhiten(coded[:length])
    return {'start': cap, 'length': length, 'cr': cr, 'crc': has_crc,
            'sync': sync, 'level': float(np.median(amps[:6])),
            'payload': payload, 'trailer': coded[length:length + 2],
            'bad_fec': sum((x.bit_count() & 1) for x in codewords[:total_bytes*2])}


if __name__ == '__main__':
    import collections, sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(STARTS)
    frames = [demod_capture(i) for i in range(limit)]
    for i, f in enumerate(frames[:20]):
        if f is None: print(i, 'empty')
        elif 'error' in f: print(i, f)
        else: print(i, f['length'], round(f['level']), f['bad_fec'], f['payload'][:48].hex(' '), repr(f['payload'][:48]))
    print(collections.Counter(f.get('error', 'ok') if f else 'empty' for f in frames))
    with open(ROOT / 'decoded_frames.jsonl', 'w') as out:
        for i, f in enumerate(frames):
            if not f or 'error' in f: continue
            out.write(json.dumps({'index': i, 'level': f['level'], 'payload': f['payload'].hex(), 'bad_fec': f['bad_fec']}) + '\n')
