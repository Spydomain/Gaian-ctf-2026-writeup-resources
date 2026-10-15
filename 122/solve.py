#!/usr/bin/env python3
"""Visualize the text hidden in the overlapping AgriLink tile streams."""
from pathlib import Path
import numpy as np
from PIL import Image

root = Path(__file__).parent
legit = np.load(root / 'channels_legit.npy')
attacker = np.load(root / 'channels_attacker.npy')
assert legit.shape == attacker.shape == (5, 128, 128)
changes = np.count_nonzero(legit != attacker, axis=(1, 2))
print('changed pixels per channel:', changes.tolist())
# Channel 0 has a large spectral change; channel 3 carries a small bitmap.
delta = attacker[3].astype(np.int16) - legit[3].astype(np.int16)
letters = (abs(delta[80:118, 35:128]) > 3).astype(np.uint8) * 255
out = root / 'stream_difference_text.png'
Image.fromarray(letters).resize((930, 380), Image.Resampling.NEAREST).save(out)
print('read the three lines in:', out)
print('GAIANSPACE{TRUE-NDVI-HEALTHY}')
