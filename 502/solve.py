#!/usr/bin/env python3
"""Evaluate the designed gate network, ignoring post-dose SHORTED annotations."""
from pathlib import Path
import re

lines = (Path(__file__).resolve().parent / 'status_encoder.netlist').read_text().splitlines()
gates = []
for line in lines:
    match = re.match(r'([no]\d+) = (XOR|NOT) ([ni]\d+)(?: ([ni]\d+))?', line)
    if match:
        gates.append(match.groups())
probes = next(line.split()[1:] for line in lines if line.startswith('PROBES '))
output = bytearray()
for probe in probes:
    number = int(probe, 16)
    signals = {f'i{bit}': (number >> bit) & 1 for bit in range(8)}
    for name, op, left, right in gates:
        signals[name] = signals[left] ^ signals[right] if op == 'XOR' else 1 - signals[left]
    output.append(sum(signals[f'o{bit}'] << bit for bit in range(8)))
flag = output.decode('ascii')
assert flag.startswith('GAIANSPACE{') and flag.endswith('}')
print(flag)
