#!/usr/bin/env python3
"""Find the single set register bit, validate CRC, and unseal the payload."""
from pathlib import Path
import hashlib
import zlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

ROOT = Path(__file__).resolve().parent
blob = (ROOT / 'reg_dump.bin').read_bytes()
damaged = blob[:32]
expected_crc = int.from_bytes(blob[32:36], 'little')
ciphertext = blob[36:]
solutions = []
for bit in range(256):
    if not damaged[bit // 8] & (1 << (bit % 8)):
        continue  # The latch-up set one bit high.
    healthy = bytearray(damaged)
    healthy[bit // 8] ^= 1 << (bit % 8)
    if zlib.crc32(healthy) == expected_crc:
        key = hashlib.sha256(healthy).digest()[:16]
        flag = unpad(AES.new(key, AES.MODE_ECB).decrypt(ciphertext), 16).decode()
        solutions.append((bit, flag))
assert len(solutions) == 1
bit, flag = solutions[0]
assert flag.startswith('GAIANSPACE{') and flag.endswith('}')
print('Recovered register:', f'R{bit // 32}', 'bit:', bit % 32)
print(flag)
