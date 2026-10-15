#!/usr/bin/env python3
"""Identify the non-blank chiral compound and calculate its L excess."""
import csv
from pathlib import Path

root = Path(__file__).resolve().parent

def rows(name):
    with (root / name).open(newline="") as source:
        return list(csv.DictReader(source))

standards = rows("standards.csv")
sample = rows("moonlet_sample.csv")
blank = rows("procedural_blank.csv")
isotopes = rows("isotopes.csv")

def near(records, time, tolerance=0.03):
    found = [row for row in records if abs(float(row["rt_min"]) - time) < tolerance]
    return found[0] if found else None

compound = "aspartic_acid"
signal = {}
for standard in standards:
    if standard["compound"] != compound:
        continue
    time = float(standard["retention_min"])
    ion = "m" + standard["quant_ion_mz"]
    peak = near(sample, time)
    assert peak and near(blank, time) is None
    isotope = near(isotopes, time)
    assert isotope and float(isotope["d13C_permil_VPDB"]) > 20
    assert float(isotope["d15N_permil_AIR"]) > 80
    signal[standard["enantiomer"]] = int(peak[ion])

excess = (signal["L"] - signal["D"]) / (signal["L"] + signal["D"]) * 100
flag = f"GAIANSPACE{{{compound}_L{round(excess)}}}"
assert flag == "GAIANSPACE{aspartic_acid_L34}"
print(f"L={signal['L']}, D={signal['D']}, ee={excess:.2f}%: {flag}")
