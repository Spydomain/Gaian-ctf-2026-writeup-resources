#!/usr/bin/env python3
"""Plot the west ripeness error and the east job destination."""
from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import shape
from sklearn.cluster import KMeans

root = Path(__file__).resolve().parent
out = root.parent / 'writeup_assets' / '127_mast_dealer.png'
morning = np.load(root / 'agrilink_tiles.npy')[2]
dealer = np.load(root / 'dealer_tile.npy')
features = json.loads((root / 'szotyola_parcels_2025.geojson').read_text())['features']
bad_ids = {'SZAPMT', 'SZC7HT', 'SZEAAL', 'SZMMPR', 'SZRUKL', 'SZXYMY'}

def ndvi(tile, nir, red):
    a, b = tile[nir].astype(float), tile[red].astype(float)
    return (a - b) / (a + b + 1e-9)

mast = ndvi(morning, 0, 1)
true = ndvi(morning, 3, 2)
classes = KMeans(n_clusters=7, random_state=42, n_init=10).fit_predict(
    dealer.reshape(5, -1).T.astype(float)).reshape(128, 128)

fig, axes = plt.subplots(1, 3, figsize=(17, 6), constrained_layout=True)
axes[0].imshow(mast, origin='upper', cmap='RdYlGn', vmin=0.25, vmax=0.75)
axes[1].imshow(true, origin='upper', cmap='RdYlGn', vmin=0.25, vmax=0.75)
axes[2].imshow(classes, origin='upper', cmap='tab10', vmin=0, vmax=9)
for ax, title in zip(axes, [
    'West: mast NDVI from altered band order',
    'West: true B08/B04 NDVI',
    'East: seven-class dealer job map',
]):
    ax.set_title(title, fontsize=11)
    ax.set_xlim(0, 128)
    ax.set_ylim(128, 0)
    ax.set_xlabel('Tile column')
    ax.set_ylabel('Tile row')

for f in features:
    name = f['properties']['parcel']
    geom = shape(f['geometry'])
    pieces = list(geom.geoms) if hasattr(geom, 'geoms') else [geom]
    for side, ax_ids, highlight in [
        (0, [0, 1], name in bad_ids),
        (128, [2], name == 'SZ4TE4'),
    ]:
        if not any(piece.bounds[0] < side + 128 and piece.bounds[2] > side
                   for piece in pieces):
            continue
        for piece in pieces:
            xy = np.asarray(piece.exterior.coords)
            for ax_id in ax_ids:
                axes[ax_id].plot(xy[:, 0] - side, xy[:, 1],
                                 color='magenta' if highlight else 'white',
                                 linewidth=1.6 if highlight else 0.45,
                                 alpha=1 if highlight else 0.45)
        if highlight:
            center = geom.representative_point()
            for ax_id in ax_ids:
                axes[ax_id].text(center.x - side, center.y, name,
                                 ha='center', va='center', fontsize=7,
                                 fontweight='bold', color='white',
                                 bbox=dict(facecolor='#351b38', alpha=0.75,
                                           edgecolor='none', pad=1.5))

fig.suptitle('127-heads-down: six green west fields sprayed; SZ4TE4 targeted east',
             fontsize=14)
fig.savefig(out, dpi=170)
print(out)
