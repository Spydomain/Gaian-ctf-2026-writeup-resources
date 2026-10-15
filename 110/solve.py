#!/usr/bin/env python3
"""
110 - m-type

AsterOre survey of 14 near-Earth objects. One is a metal-rich (M-type) body
worth mining for platinum-group metals.

Data sources:
- spectra.csv: reflectance 0.45–2.45 µm, normalized at 0.55 µm
- survey_night.csv: H magnitude, visible albedo (thermal-IR)
- radar_notes.md: radar albedo (key metal indicator), desk notes

Analysis:
- M-type (metallic) asteroids: albedo 0.1–0.3, featureless spectra, high radar albedo (>0.3)
- E-type (enstatite): very high albedo (>0.4), featureless, NOT metallic
- C/P-type: very low albedo (<0.1), featureless, carbonaceous
- S-type: moderate albedo, strong 1 & 2 µm silicate absorption bands

Key clues:
- Kaito: "Metal is shiny. Sort by albedo, take the brightest flat spectrum. QF8."
- Sunniva: "Shiny is not the same as metal. Read the whole sheet."
- Coffee on printout, but 1 µm region readable → 1 µm absorption is key diagnostic.
- Radar albedo is the best metal indicator; only QM23 has explicit radar albedo (0.41).

Analysis of all 14 objects:
- QF8: albedo 0.520 (E-type, not metal), no 1µm absorption, Kaito's pick
- QR7/QD12/QS15/QP19: very low albedo (<0.1), carbonaceous
- QN2/QW9/QY14/QJ30/QA4/QV21: significant 1µm absorption (silicates)
- QM23: radar albedo 0.41 (metal!), albedo 0.180 (M-type range), weak 1µm abs, no 2µm abs
- QU3: albedo 0.470 (E-type)
- QX26: albedo 0.060 (carbonaceous)

Only QM23 has high radar albedo + M-type albedo + featureless spectrum.
"""
import pandas as pd
import numpy as np
import json

SPECTRA = "110/spectra.csv"
SURVEY = "110/survey_night.csv"

spectra = pd.read_csv(SPECTRA)
survey = pd.read_csv(SURVEY)
wl = spectra['wavelength_um'].values
rocks = spectra.columns[1:]

def abs_depth(refl, center):
    idx_c = np.argmin(np.abs(wl - center))
    idx_l = np.argmin(np.abs(wl - (center - 0.1)))
    idx_r = np.argmin(np.abs(wl - (center + 0.1)))
    r_lin = (refl[idx_l] + refl[idx_r]) / 2
    return (r_lin - refl[idx_c]) / r_lin if r_lin > 0 else 0

# Diameter from H and pV
survey['diam_m'] = 1329 / np.sqrt(survey['pV']) * 10**(-survey['H_mag']/5) * 1000
survey['diam_m_rnd'] = np.round(survey['diam_m'] / 10) * 10

# Find the M-type candidate
candidates = []
for _, row in survey.iterrows():
    desig = row['designation']
    col = desig.replace(' ', '_')
    refl = spectra[col].values
    d1 = abs_depth(refl, 1.0)
    d2 = abs_depth(refl, 2.0)
    flat = np.std(spectra[col].values)
    slope = np.polyfit(wl, spectra[col].values, 1)[0]
    candidates.append({
        'desig': desig,
        'H': row['H_mag'],
        'pV': row['pV'],
        'diam_m': int(row['diam_m_rnd']),
        'd1': d1,
        'd2': d2,
        'flat': flat,
        'slope': slope
    })

# M-type criteria: albedo 0.1-0.3, weak/no 1µm absorption, no 2µm absorption, flat
# Radar albedo 0.41 for QM23 is the smoking gun
for c in candidates:
    is_metal = (0.1 <= c['pV'] <= 0.3 and
                c['d1'] < 0.02 and
                c['d2'] < 0.02 and
                c['flat'] < 0.15)
    print(f"{c['desig']:>10} pV={c['pV']:.3f} D={c['diam_m']}m "
          f"1µm={c['d1']:.4f} 2µm={c['d2']:.4f} flat={c['flat']:.4f} "
          f"{'✓ METAL' if is_metal else ''}")

# The answer
target = [c for c in candidates if c['desig'] == '2041 QM23'][0]
flag = f"GAIANSPACE{{{target['desig'].replace(' ', '')}_{target['diam_m']}}}"
print(f"\n{flag}")