#!/usr/bin/env python3
"""Find summer tile deliveries inconsistent with harvested winter wheat."""
import json
import re
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
fields = json.loads((ROOT / 'rica_parcels_2024.geojson').read_text())['features']
wheat = next(f for f in fields if f['properties']['crop_2024'] == 'őszi búza')
canvas = Image.new('1', (256, 256))
ImageDraw.Draw(canvas).polygon([tuple(p) for p in wheat['geometry']['coordinates'][0]], fill=1)
mask = np.asarray(canvas, dtype=bool)

ndvi_by_date = {}
with zipfile.ZipFile(ROOT / 'rica_tiles_2024.zip') as archive:
    for name in archive.namelist():
        raw = archive.read(name)
        # The five byte-valued planes follow the ASCII header: B02 B03 B04 B08 B11.
        values = np.frombuffer(raw[raw.index(b'\n') + 1:], dtype=np.uint8)
        bands = values.reshape(5, 256, 256).astype(float)
        ndvi = (bands[3] - bands[2]) / (bands[3] + bands[2] + 1e-9)
        date = Path(name).stem.split('_')[-1]
        ndvi_by_date[date] = float(np.median(ndvi[mask]))

suspect = {date for date, ndvi in ndvi_by_date.items()
           if '202407' <= date[:6] <= '202408' and ndvi > 0.5}
ids = []
for line in (ROOT / 'rica_mast_journal.log').read_text().splitlines():
    match = re.search(r'tile (\d{8})\s+delivery ([A-Z0-9]{4})', line)
    if match and match[1] in suspect:
        ids.append(match[2])

assert len(ids) == 4
for date in sorted(ndvi_by_date):
    print(date, round(ndvi_by_date[date], 3), '*' if date in suspect else '')
print('GAIANSPACE{' + '-'.join(ids) + '}')
