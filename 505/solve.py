#!/usr/bin/env python3
"""Fit the thermal recurrence from the known flag prefix, then invert it."""
from pathlib import Path
import csv
import numpy as np

ROOT = Path(__file__).resolve().parent
with (ROOT / 'thermal_log.csv').open() as stream:
    temperature = np.array([float(row['temp_c']) for row in csv.DictReader(stream)])
delta = np.diff(temperature)
prefix = b'GAIANSPACE{'
# Delta T = K*P - (1/tau)*T + Tamb/tau.
design = np.column_stack([list(prefix), -temperature[:len(prefix)],
                          np.ones(len(prefix))])
K, inverse_tau, ambient_over_tau = np.linalg.lstsq(design, delta[:len(prefix)], rcond=None)[0]
drive = (delta + inverse_tau * temperature[:-1] - ambient_over_tau) / K
assert np.max(np.abs(drive - np.rint(drive))) < 1e-3
flag = bytes(np.rint(drive).astype(np.uint8)).decode()
assert flag.startswith(prefix.decode()) and flag.endswith('}')
print(f'K={K:.5f}, tau={1/inverse_tau:.2f} s, Tamb={ambient_over_tau/inverse_tau:.2f} C')
print(flag)
