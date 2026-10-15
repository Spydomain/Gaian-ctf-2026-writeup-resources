#!/usr/bin/env python3
"""Integrate the DR-ONE thrust plan using the order stated in gfold_notes.md."""
import csv
from pathlib import Path

root = Path(__file__).resolve().parent
position = [2000.0, -500.0, 1500.0]
velocity = [-40.0, 10.0, -60.0]
dt = 0.1
gravity = 3.711

with (root / "descent_profile.csv").open(newline="") as source:
    for row in csv.DictReader(source):
        acceleration = [float(row["thr_ax"]), float(row["thr_ay"]),
                        float(row["thr_az"]) - gravity]
        velocity = [v + a * dt for v, a in zip(velocity, acceleration)]
        position = [p + v * dt for p, v in zip(position, velocity)]
        if position[2] <= 0:
            break
    else:
        raise RuntimeError("ground contact is absent from the supplied plan")

x, y = (round(value / 10) * 10 for value in position[:2])
flag = f"GAIANSPACE{{LZ_{x}_{y}}}"
assert flag == "GAIANSPACE{LZ_1370_-360}"
print(f"contact at {row['t_s']} s: {position}; {flag}")
