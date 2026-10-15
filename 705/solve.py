#!/usr/bin/env python3
"""Descramble and compare the five Pilgrim-1 memory readouts."""
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent


def descramble(blob, readout, frame):
    state = ((readout << 8) | frame) ^ 0x5A5A
    result = bytearray()
    for byte in blob:
        mask = 0
        for bit in range(8):
            outgoing = state & 1
            mask |= outgoing << bit
            state = (state >> 1) ^ (0xB400 if outgoing else 0)
        result.append(byte ^ mask)
    return result


def frames():
    for line in (ROOT / 'readout_frames.log').read_text().splitlines():
        if line.startswith('#') or not line.strip():
            continue
        station, time, snr, length, hexdata = line.split()
        data = bytes.fromhex(hexdata)
        assert data[:2] == b'P1' and len(data) == int(length)
        readout, frame = data[2:4]
        address = int.from_bytes(data[4:6], 'big')
        decoded = descramble(data[6:], readout, frame)
        assert len(decoded) % 2 == 0
        words = [int.from_bytes(decoded[i:i+2], 'big') for i in range(0, len(decoded), 2)]
        values, checksum = words[:-1], words[-1]
        assert address == frame * 80 and len(values) == min(80, 2048 - address)
        yield readout, frame, address, values, (sum(values) & 0xFFFF) == checksum, snr


def main():
    golden = (ROOT / 'fds_golden.img').read_bytes()
    expected = [int.from_bytes(golden[i:i+2], 'big') for i in range(0, len(golden), 2)]
    for line in (ROOT / 'uplink_2026-10-11.txt').read_text().splitlines():
        if not line.startswith('#') and line.strip():
            address, word = line.split()[:2]
            expected[int(address, 16)] = int(word, 16)
    observed = defaultdict(dict)
    verified = defaultdict(dict)
    stats = Counter()
    for readout, frame, address, values, valid, snr in frames():
        stats['frames'] += 1
        stats['good' if valid else 'bad'] += 1
        stats[f'bad-{frame}' if not valid else f'good-{frame}'] += 1
        for index, word in enumerate(values):
            observed[address + index][readout] = word
            if valid:
                verified[address + index][readout] = word
    print('Frames:', stats['frames'], 'valid:', stats['good'], 'invalid:', stats['bad'])
    # These are workspace/return-address words written by the running FDS,
    # plus two words installed by the undocumented 1998 thermal load.
    mutable = {0x040, 0x0C0, 0x0E0, 0x0E1, 0x0E3, 0x0E6,
               0x3A0, 0x3B1, 0x5D0, 0x772, 0x778}
    damaged = []
    for address in range(2048):
        if 0x600 <= address < 0x700 or address in mutable:
            continue
        clean_votes = Counter(verified[address].values())
        if len(clean_votes) == 1 and len(verified[address]) >= 2:
            word = next(iter(clean_votes))
            agreeing = sum(v == word for v in observed[address].values())
            if word != expected[address] and agreeing >= 3:
                damaged.append(address)
                print(f'{address:03X}: {expected[address]:04X} -> {word:04X} '
                      f'({agreeing}/5 reads; {len(verified[address])} valid frames)')
    # The one-off 7CA flip is in a checksum-valid frame; its four other
    # readouts contain the golden word. It is a transient cell failure.
    transient = []
    mutable_or_known = mutable | set(range(0x600, 0x700)) | set(damaged)
    for readout, frame, address, values, valid, snr in frames():
        if not valid:
            continue
        differences = [address + i for i, word in enumerate(values)
                       if address + i not in mutable_or_known
                       and word != expected[address + i]]
        if len(differences) == 1:
            cell = differences[0]
            if sum(word == expected[cell] for word in observed[cell].values()) >= 4:
                transient.append(cell)
    transient = sorted(set(transient))
    assert transient == [0x7CA], transient
    assert observed[0x7CA][2] ^ expected[0x7CA] == 0x8000
    print('7CA:', ' '.join(f'{r}:{observed[0x7CA][r]:04X}' for r in range(1, 6)))
    print('Persistent differences:', '-'.join(f'{addr:03X}' for addr in damaged))
    addresses = sorted(damaged + transient)
    flag = 'GAIANSPACE{' + '-'.join(f'{addr:03X}' for addr in addresses) + '}'
    assert flag == 'GAIANSPACE{405-43E-445-448-4BD-7CA}'
    print(flag)


if __name__ == '__main__':
    main()
