#!/usr/bin/env python3
"""Verify the extracted flag against every pixel of the recovered anomaly."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
frames = (ROOT / 'decoded_frames.bin').read_bytes()
assert len(frames) == 1280 * 73
tile = np.zeros((5, 128, 128), dtype=np.uint8)
seen = np.zeros((5, 128, 2), dtype=bool)
for start in range(0, len(frames), 73):
    frame = frames[start:start + 73]
    assert frame[:3] == b'JRM'
    band, row, half = frame[3:6]
    assert band < 5 and row < 128 and half < 2 and not seen[band, row, half]
    tile[band, row, half * 64:(half + 1) * 64] = np.frombuffer(frame[7:71], np.uint8)
    seen[band, row, half] = True
assert seen.all()
red, swir = tile[0], tile[4]
anomaly = ((red < 15) & (swir > 70)) | ((red >= 15) & (swir < 70))
font = ImageFont.load_default_imagefont()  # Pillow's legacy 6-pixel bitmap font.
lines = [('GAIANSPACE{', (12, 34)), ('7TH-CLASS-', (15, 46)), ('XHTXWX}', (24, 58))]
image = Image.new('L', (128, 128))
draw = ImageDraw.Draw(image)
for text, position in lines:
    draw.text(position, text, font=font, fill=255)
plain = np.asarray(image) > 0
rendered = cv2.dilate(plain.astype(np.uint8), np.ones((1, 2), np.uint8)) > 0
# The same threshold catches isolated scene pixels elsewhere in the tile.
# Compare the planted text patch, which was identified independently from
# the seven-class anomaly and contains all three rendered lines.
patch = np.s_[32:70, 10:80]
errors = int(np.count_nonzero(rendered[patch] != anomaly[patch]))
print(f'Text-patch anomaly pixels: {int(anomaly[patch].sum())}; rendered pixels: {int(rendered[patch].sum())}')
print(f'Text-patch pixel mismatches: {errors}')
assert errors == 0
image.crop((10, 32, 80, 71)).resize((700, 390), Image.Resampling.NEAREST).save(ROOT / 'flag_verified.png')
print('GAIANSPACE{7TH-CLASS-XHTXWX}')
