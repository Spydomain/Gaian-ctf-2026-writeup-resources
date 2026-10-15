#!/usr/bin/env python3
"""Fit the light curve and ballistically time the viable anchor release."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).parent
phot = pd.read_csv(ROOT / 'hover_photometry.csv')
epoch = pd.Timestamp(phot.utc.iloc[0])
t = (pd.to_datetime(phot.utc) - epoch).dt.total_seconds().to_numpy()
mag = phot.rel_mag.to_numpy()


def curve(period, harmonics=8):
    phase = 2 * np.pi * t / period
    basis = np.column_stack([np.ones(len(t))] +
                            [f(k * phase) for k in range(1, harmonics + 1)
                             for f in (np.sin, np.cos)])
    coefficients = np.linalg.lstsq(basis, mag, rcond=None)[0]
    return np.mean((mag - basis @ coefficients) ** 2), coefficients


# The dominant double-wave is one-half rotation; a weaker unequal-face term
# breaks that ambiguity. Fit the full rotation to both terms at once.
fit = minimize_scalar(lambda p: curve(p)[0], bounds=(5840, 5860),
                      method='bounded', options={'xatol': 1e-7})
period = fit.x
coefficients = curve(period)[1]
phases = np.linspace(0, 1, 100_001, endpoint=False)
angles = 2 * np.pi * phases
basis = np.column_stack([np.ones(len(phases))] +
                        [f(k * angles) for k in range(1, 9)
                         for f in (np.sin, np.cos)])
model = basis @ coefficients
bright_face_phase = phases[np.argmin(model)]  # smaller magnitude = brighter

mu = 0.2123
def fall_time(speed):
    return quad(lambda r: 1 / np.sqrt(speed**2 + 2*mu*(1/r - 1/500)),
                50, 500, epsabs=1e-8)[0]

contact_speeds = {name: np.sqrt(speed**2 + 2*mu*(1/50 - 1/500))
                  for name, speed in [('A', .020), ('B', .080)]}
assert contact_speeds['A'] < .110 < contact_speeds['B']
arrival_offset = (pd.Timestamp('2041-11-04T16:00:00') - epoch).total_seconds() + fall_time(.020)
slots = np.arange(540)
arrival_phases = ((arrival_offset + 10*slots) / period) % 1
phase_error = (arrival_phases - bright_face_phase + .5) % 1 - .5
best = int(np.argmin(abs(phase_error)))
print(f'rotation period: {period:.5f} s; bright-face phase: {bright_face_phase:.5f}')
print(f'fall time A: {fall_time(.020):.5f} s')
print('contact speed m/s:', contact_speeds)
print(f'closest slot: {best:04d}, angle error: {phase_error[best]*360:+.3f} degrees')
print(f'GAIANSPACE{{A-{best:04d}}}')
