#!/usr/bin/env python3
"""Realign padded transport bursts and read the SDT service name."""
import re
from pathlib import Path

data = (Path(__file__).resolve().parent / "halcyon_dump.bin").read_bytes()
offsets = []
start = 0
while start + 376 <= len(data):
    if data[start] == 0x47 and data[start + 188] == 0x47:
        end = start
        while end + 188 < len(data) and data[end + 188] == 0x47:
            end += 188
        offsets.extend(range(start, end + 1, 188))
        start = end + 188
    else:
        start += 1

sdt_payloads = []
for offset in offsets:
    packet = data[offset:offset + 188]
    if len(packet) != 188 or ((packet[1] & 0x1f) << 8 | packet[2]) != 0x11:
        continue
    adaptation = (packet[3] >> 4) & 3
    cursor = 4 + (1 + packet[4] if adaptation in (2, 3) else 0)
    if adaptation in (1, 3):
        sdt_payloads.append(packet[cursor:])

service_data = b"".join(sdt_payloads)
match = re.search(rb"(?:[\x20-\x7e]\x00){10,}", service_data)
assert match
text = match.group().decode("utf-16le")
# The descriptor uses UTF-16LE for the name but its final closing brace is
# retained as a single byte immediately before the descriptor trailer.
if service_data[match.end():match.end() + 1] == b"}":
    text += "}"
flag = re.search(r"GAIANSPACE\{[^}]+\}", text).group()
assert flag == "GAIANSPACE{burst_r3align_sdt_r3ad}"
print(f"{len(offsets)} aligned packets, {len(sdt_payloads)} SDT packets: {flag}")
