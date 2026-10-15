#!/usr/bin/env python3
"""Recover the short xorshift32 stream state from the known dump magic."""
from pathlib import Path
import re
from z3 import BitVec, Extract, LShR, Solver, sat

ROOT = Path(__file__).resolve().parent
packets = [(ROOT / f'packet_{number}.bin').read_bytes() for number in range(1, 5)]
for index in (0, 1, 3):
    assert packets[index][:6] == b'DMP\x01' + bytes((index, 4))

# The third frame had ten FEC symbol errors. The prior radio rerun corrected
# six ciphertext bytes; the clean combined stream is retained as cipher.bin.
third = bytearray(packets[2][6:-2])
repairs = {0: 0x25, 2: 0x5C, 4: 0x97, 6: 0xE3, 14: 0x86, 15: 0xC3}
for offset, value in repairs.items():
    third[offset] = value
ciphertext = packets[0][6:-2] + packets[1][6:-2] + third + packets[3][6:-2]
assert len(ciphertext) == 195
assert ciphertext == (ROOT / 'cipher.bin').read_bytes()

known = b'G723MEM'
observed_stream = bytes(a ^ b for a, b in zip(ciphertext, known))
seed = BitVec('seed', 32)
state = seed
solver = Solver()
for value in observed_stream:
    solver.add(Extract(7, 0, state) == value)
    state = state ^ (state << 13)
    state = state ^ LShR(state, 17)
    state = state ^ (state << 5)
assert solver.check() == sat
recovered_seed = solver.model()[seed].as_long()
solver.add(seed != recovered_seed)
assert solver.check() != sat  # The seven bytes determine one 32-bit state.

state = recovered_seed
clear = bytearray()
for value in ciphertext:
    clear.append(value ^ (state & 0xFF))
    state ^= (state << 13) & 0xFFFFFFFF
    state ^= state >> 17
    state ^= (state << 5) & 0xFFFFFFFF
    state &= 0xFFFFFFFF
record = clear.decode('ascii')
assert record.startswith('G723MEM1|BANK2|') and record.endswith(';END')
flag = re.search(r'SECRET_STORE:(GAIANSPACE\{[^}]+\})', record).group(1)
print('xorshift32 seed:', hex(recovered_seed))
print(record)
print(flag)
