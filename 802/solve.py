#!/usr/bin/env python3
"""Validate MPE section CRCs, then order UDP fragment payloads."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
transport = (ROOT / 'eumetcast_grab.ts').read_bytes()
assert len(transport) % 188 == 0


def mpeg_crc(data):
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            crc = ((crc << 1) ^ (0x04C11DB7 if crc & 0x80000000 else 0)) & 0xFFFFFFFF
    return crc


segments = {}
rejected = 0
for start in range(0, len(transport), 188):
    packet = transport[start:start + 188]
    assert packet[0] == 0x47
    pid = (packet[1] & 0x1F) << 8 | packet[2]
    if pid != 0x12C or not packet[1] & 0x40:
        continue
    pointer = packet[4]
    data = packet[5 + pointer:]
    length = ((data[1] & 0x0F) << 8) | data[2]
    section = data[:3 + length]
    if mpeg_crc(section):
        rejected += 1
        continue
    assert section[0] == 0x3E
    ip = section[12:-4]
    ihl = (ip[0] & 0x0F) * 4
    assert ip[0] >> 4 == 4 and ip[9] == 17
    udp = ip[ihl:]
    udp_length = int.from_bytes(udp[4:6], 'big')
    message = udp[8:udp_length].decode('ascii')
    match = re.fullmatch(r'SEG(\d\d)\|(.+)', message)
    assert match
    segments[int(match[1])] = match[2]
assert sorted(segments) == list(range(len(segments)))
flag = ''.join(segments[index] for index in sorted(segments))
assert flag.startswith('GAIANSPACE{') and flag.endswith('}')
print('Valid sections:', len(segments), 'rejected by CRC:', rejected)
print(flag)
