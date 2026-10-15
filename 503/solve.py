#!/usr/bin/env python3
"""Remove displacement-damage drift and infer the fixed CO2 baseline."""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parent
with (ROOT / 'sensor_log.csv').open() as stream:
    rows = list(csv.DictReader(stream))
corrected = []
for row in rows:
    n = int(row['sample_n'])
    drift = round(1.7 * n + 0.013 * n * n)
    corrected.append(int(row['co2_ppm']) - drift)
prefix = 'GAIANSPACE{'
baselines = {value - ord(letter) for value, letter in zip(corrected, prefix)}
assert len(baselines) == 1, baselines
baseline = baselines.pop()
flag = ''.join(chr(value - baseline) for value in corrected)
assert flag.startswith(prefix) and flag.endswith('}')
print('Fixed baseline:', baseline, 'ppm')
print(flag)
