#!/usr/bin/env python3
"""Select CanSat LoRa frames, order by sequence, and remove sync-byte XOR."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
frames = {}
for line in (ROOT / 'lora_capture.log').read_text().splitlines():
    match = re.search(r'addr=0x([0-9A-Fa-f]+) seq=([0-9A-Fa-f]+).*?payload=([0-9a-f]+)', line)
    if not match or int(match[1], 16) != 0x1F:
        continue
    sequence = int(match[2], 16)
    payload = bytes(byte ^ 0x12 for byte in bytes.fromhex(match[3]))
    frames[sequence] = payload
assert sorted(frames) == list(range(len(frames)))
flag = b''.join(frames[sequence] for sequence in sorted(frames)).decode()
assert flag.startswith('GAIANSPACE{') and flag.endswith('}')
print('CanSat frames:', len(frames))
print(flag)
