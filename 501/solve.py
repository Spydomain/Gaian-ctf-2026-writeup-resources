#!/usr/bin/env python3
"""Repair one AES key bit and decrypt the padded two-block flag."""
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

ROOT = Path(__file__).resolve().parent
damaged = (ROOT / 'corrupted.key').read_bytes()
ciphertext = (ROOT / 'cipher.bin').read_bytes()
assert len(damaged) == 16 and len(ciphertext) % 16 == 0
solutions = []
for bit in range(128):
    key = bytearray(damaged)
    key[bit // 8] ^= 1 << (bit % 8)
    plaintext = AES.new(bytes(key), AES.MODE_ECB).decrypt(ciphertext)
    try:
        message = unpad(plaintext, 16).decode('ascii')
    except (ValueError, UnicodeDecodeError):
        continue
    if message.startswith('GAIANSPACE{') and message.endswith('}'):
        solutions.append((bit, message))
assert len(solutions) == 1, solutions
print('Flipped key bit:', solutions[0][0])
print(solutions[0][1])
