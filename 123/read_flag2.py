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

# Combined anomaly mask (classes 3 and 5)
anomaly_mask = ((class_map == 3) | (class_map == 5)).astype(np.uint8)

# Focus on the text region: rows 36-67
# Line 1: rows 36-43 (GAIANSPACE{)
# Line 2: rows 48-54
# Line 3: rows 60-67

print('=== LINE 1 (rows 36-43) ===')
for r in range(36, 44):
    line = ''
    for c in range(128):
        line += '#' if anomaly_mask[r, c] else '.'
    print(f'{r}: {line}')

print('\n=== LINE 2 (rows 48-54) ===')
for r in range(48, 55):
    line = ''
    for c in range(128):
        line += '#' if anomaly_mask[r, c] else '.'
    print(f'{r}: {line}')

print('\n=== LINE 3 (rows 60-67) ===')
for r in range(60, 68):
    line = ''
    for c in range(128):
        line += '#' if anomaly_mask[r, c] else '.'
    print(f'{r}: {line}')

# Save a zoomed version of just the text rows  
text_only = anomaly_mask[35:69, :]
scale = 8
big = np.repeat(np.repeat(text_only * 255, scale, axis=0), scale, axis=1)
Image.fromarray(big).save('flag_text_zoomed_8x.png')
print('\nSaved flag_text_zoomed_8x.png')
