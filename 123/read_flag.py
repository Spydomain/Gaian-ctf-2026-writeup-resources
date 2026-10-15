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

# Classes 3 and 5 are the anomalous ones - combine them as the "flag text"
# Class 3: center [8, 15, 9, 107, 97] - high NIR AND high SWIR
# Class 5: center [25, 32, 44, 63, 47] - moderate values, different spectral signature
anomaly_mask = ((class_map == 3) | (class_map == 5)).astype(np.uint8)

# Find bounding box
rows, cols = np.where(anomaly_mask)
r_min, r_max = rows.min(), rows.max()
c_min, c_max = cols.min(), cols.max()
print(f'Anomaly bounding box: rows {r_min}-{r_max}, cols {c_min}-{c_max}')
print(f'Anomaly size: {r_max-r_min+1} x {c_max-c_min+1}')

# Extract the text region
text_region = anomaly_mask[r_min:r_max+1, c_min:c_max+1]
print(f'Text region shape: {text_region.shape}')
print()

# Print as ASCII art
print('=== ANOMALY TEXT (# = anomaly pixel) ===')
for r in range(text_region.shape[0]):
    line = ''
    for c in range(text_region.shape[1]):
        line += '#' if text_region[r, c] else '.'
    print(f'{r_min+r:3d}: {line}')

# Save high-res version
scale = 8
big = np.repeat(np.repeat(text_region * 255, scale, axis=0), scale, axis=1)
Image.fromarray(big).save('flag_text_combined_8x.png')
print('\nSaved flag_text_combined_8x.png')

# Also try just class 3 (high NIR + high SWIR - the most anomalous)
anomaly3 = (class_map == 3).astype(np.uint8)
text3 = anomaly3[r_min:r_max+1, c_min:c_max+1]
print('\n=== CLASS 3 ONLY ===')
for r in range(text3.shape[0]):
    line = ''
    for c in range(text3.shape[1]):
        line += '#' if text3[r, c] else '.'
    print(f'{r_min+r:3d}: {line}')

# And class 5 only
anomaly5 = (class_map == 5).astype(np.uint8)
text5 = anomaly5[r_min:r_max+1, c_min:c_max+1]
print('\n=== CLASS 5 ONLY ===')
for r in range(text5.shape[0]):
    line = ''
    for c in range(text5.shape[1]):
        line += '#' if text5[r, c] else '.'
    print(f'{r_min+r:3d}: {line}')
