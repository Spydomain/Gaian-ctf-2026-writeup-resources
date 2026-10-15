import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')
pixels = tile.reshape(5, -1).T
kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
labels = kmeans.fit_predict(pixels.astype(float))
class_map = labels.reshape(128, 128)

# Try just class 3 alone (the strongest anomaly)
for cls_id in [3, 5]:
    anomaly_mask = (class_map == cls_id).astype(np.uint8)
    
    print(f'\n{"="*80}')
    print(f'CLASS {cls_id} ONLY')
    print(f'{"="*80}')
    
    lines_data = [
        (37, 42, "Line 1"),
        (48, 54, "Line 2"),
        (61, 66, "Line 3"),
    ]
    
    for y0, y1, name in lines_data:
        sub = anomaly_mask[y0:y1+1, :]
        print(f'\n{name} (rows {y0}-{y1}):')
        for r in range(y0, y1+1):
            line = ''
            for c in range(128):
                line += '#' if anomaly_mask[r, c] else '.'
            # Trim trailing dots
            line = line.rstrip('.')
            if '#' in line:
                print(f'{r}: {line}')

# Now let me also try different numbers of clusters
print('\n\n' + '='*80)
print('Trying different cluster counts to find cleaner separation')
print('='*80)

for n_clusters in [5, 8, 10, 12, 15]:
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    lab = km.fit_predict(pixels.astype(float))
    cm = lab.reshape(128, 128)
    
    print(f'\n--- {n_clusters} clusters ---')
    for i in range(n_clusters):
        count = np.sum(lab == i)
        center = km.cluster_centers_[i].astype(int)
        north_count = np.sum(cm[:64, :] == i)
        if count > 0:
            north_pct = north_count / count * 100
            if 50 < count < 1000:  # minority classes
                print(f'  Class {i}: {count} px, center={center}, {north_pct:.0f}% in north')
