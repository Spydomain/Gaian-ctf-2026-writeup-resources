#!/usr/bin/env python3
"""Decode DiSEqC GotoX angles and assemble catalog fragments in TX order."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
catalog = json.loads((ROOT / 'catalog.json').read_text())['slots']
by_angle = {slot['motor_angle_deg']: slot for slot in catalog}
fragments = []
for line in (ROOT / 'slew_log.txt').read_text().splitlines():
    match = re.search(r'\bTX (e0316e[0-9a-f]{4})\b', line)
    if not match:
        continue
    command = bytes.fromhex(match[1])
    high, low = command[-2:]
    # DiSEqC GotoX: E means east, D means west. Integer degrees are a
    # 5-bit nibble pair; the low nibble counts sixteenths of a degree.
    direction = 1 if high >> 4 == 0xE else -1
    assert high >> 4 in (0xD, 0xE)
    angle = direction * ((high & 0x0F) * 16 + (low >> 4) + (low & 0x0F) / 16)
    slot = by_angle[angle]
    print(match[1], f'{angle:+g}', slot['callsign'], slot['fragment'])
    fragments.append(slot['fragment'])
flag = ''.join(fragments)
assert flag.startswith('GAIANSPACE{') and flag.endswith('}')
print(flag)
