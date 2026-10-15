#!/usr/bin/env python3
"""Unwrap DVB BB frames, reassemble GSE fragments, and check their CRC32."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
transport = (ROOT / 'relay_bbframes.ts').read_bytes()
assert len(transport) % 188 == 0


def crc8_dvb(data):
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = ((value << 1) ^ (0xD5 if value & 0x80 else 0)) & 0xFF
    return value


def crc32_mpeg(data):
    value = 0xFFFFFFFF
    for byte in data:
        value ^= byte << 24
        for _ in range(8):
            value = ((value << 1) ^ (0x04C11DB7 if value & 0x80000000 else 0)) & 0xFFFFFFFF
    return value


open_fragments = {}
valid_messages = []
rejected = 0
for start in range(0, len(transport), 188):
    ts = transport[start:start + 188]
    assert ts[0] == 0x47
    if ((ts[1] & 0x1F) << 8 | ts[2]) != 270:
        continue
    section = ts[5 + ts[4]:]
    section_length = ((section[1] & 0x0F) << 8) | section[2]
    section = section[:3 + section_length]
    assert section[0] == 0x80
    header = section[4:14]
    assert crc8_dvb(header) == 0
    frame = section[14:]
    offset = 0
    while offset + 2 <= len(frame):
        first, second = frame[offset:offset + 2]
        length = (first & 0x0F) << 8 | second
        if length == 0:
            break  # BB padding
        data = frame[offset + 2:offset + 2 + length]
        assert len(data) == length
        start_bit = bool(first & 0x80)
        end_bit = bool(first & 0x40)
        if start_bit and not end_bit:
            fragment_id = data[0]
            total = int.from_bytes(data[1:3], 'big')
            protocol = data[3:5]
            assert protocol == b'\x08\x00'  # IPv4
            open_fragments[fragment_id] = [total, bytearray(data[5:])]
        elif not start_bit and not end_bit:
            open_fragments[data[0]][1].extend(data[1:])
        elif not start_bit and end_bit:
            fragment_id = data[0]
            total, pdu = open_fragments.pop(fragment_id)
            pdu.extend(data[1:-4])
            expected = int.from_bytes(data[-4:], 'big')
            if len(pdu) != total - 2 or crc32_mpeg(pdu) != expected:
                rejected += 1
            else:
                ihl = (pdu[0] & 15) * 4
                assert pdu[9] == 17
                udp = pdu[ihl:]
                payload = udp[8:int.from_bytes(udp[4:6], 'big')]
                valid_messages.append(payload.decode('ascii'))
        offset += 2 + length

assert len(valid_messages) == 1 and rejected == 1
match = re.fullmatch(r'MSG\|(GAIANSPACE\{[^}]+\})', valid_messages[0])
assert match
print('Valid reassembled message:', len(valid_messages), 'CRC-rejected twin:', rejected)
print(match[1])
