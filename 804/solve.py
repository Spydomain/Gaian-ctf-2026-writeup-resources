#!/usr/bin/env python3
"""Parse the valid station-log page after the mid-page prefix."""
import re
from pathlib import Path

data = (Path(__file__).resolve().parent / "halcyon_mid.bin").read_bytes()
pages = []
for offset in range(len(data) - 14):
    if data[offset:offset + 4] != b"\x62\x00\x00\x00":
        continue
    if data[offset + 10] != 0xe0 or data[offset + 12:offset + 14] != b"\x00\xfd":
        continue
    length = data[offset + 11]
    payload = data[offset + 14:offset + 14 + length]
    if len(payload) == length:
        pages.append((offset, payload))

assert len(pages) == 2
records = []
for _, payload in pages:
    cursor = 0
    while cursor + 2 <= len(payload):
        kind, size = payload[cursor:cursor + 2]
        cursor += 2
        body = payload[cursor:cursor + size]
        assert len(body) == size
        cursor += size
        records.append((kind, body))
    assert cursor == len(payload)

assert b"payload XOR 0x5A" in next(body for kind, body in records if kind == 1)
message = bytes(value ^ 0x5a for value in next(body for kind, body in records if kind == 7)).decode()
flag = re.search(r"GAIANSPACE\{[^}]+\}", message).group()
assert flag == "GAIANSPACE{syncd_led_me_home}"
print(f"{len(pages)} pages, {len(records)} records: {flag}")
