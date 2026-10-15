import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from scipy import ndimage
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')
pixels = tile.reshape(5, -1).T
kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
labels = kmeans.fit_predict(pixels.astype(float))
class_map = labels.reshape(128, 128)

anomaly_mask = ((class_map == 3) | (class_map == 5)).astype(np.uint8)

# Apply a smoothing approach: if a pixel has 5+ out of 8 neighbors as anomaly, it IS anomaly
# This should clean up the noise
kernel = np.ones((3, 3))
neighbor_count = ndimage.convolve(anomaly_mask, kernel, mode='constant')
# Keep pixel if it has 5+ neighbors (including itself)
cleaned = (neighbor_count >= 5).astype(np.uint8)

# Also try the raw pixel values directly instead of clustering
# The anomaly was defined as high NIR + high SWIR  
# Let's look at channel values directly in the text region
nir = tile[3]
swir = tile[4]

# Threshold-based approach
nir_high = (nir > 80).astype(np.uint8)
swir_high = (swir > 80).astype(np.uint8)
both_high = nir_high & swir_high

print("=== CLEANED (majority filter) ===")
for y0, y1, name in [(36, 44, "Line 1"), (47, 55, "Line 2"), (59, 68, "Line 3")]:
    print(f'\n{name}:')
    for r in range(y0, y1+1):
        line = ''
        for c in range(128):
            line += '#' if cleaned[r, c] else '.'
        line = line.rstrip('.')
        if '#' in line:
            print(f'{r}: {line}')

print("\n\n=== NIR > 80 AND SWIR > 80 ===")
for y0, y1, name in [(36, 44, "Line 1"), (47, 55, "Line 2"), (59, 68, "Line 3")]:
    print(f'\n{name}:')
    for r in range(y0, y1+1):
        line = ''
        for c in range(128):
            line += '#' if both_high[r, c] else '.'
        line = line.rstrip('.')
        if '#' in line:
            print(f'{r}: {line}')

# Save cleaned version
text_region = cleaned[35:70, 10:80]
big = np.repeat(np.repeat(text_region * 255, 12, axis=0), 12, axis=1)
Image.fromarray(big).save('flag_cleaned_12x.png')
print('\nSaved flag_cleaned_12x.png')

# Save threshold version 
text_region2 = both_high[35:70, 10:80]
big2 = np.repeat(np.repeat(text_region2 * 255, 12, axis=0), 12, axis=1)
Image.fromarray(big2).save('flag_threshold_12x.png')
print('Saved flag_threshold_12x.png')

# Try erosion followed by dilation (opening) to clean noise
from scipy.ndimage import binary_opening, binary_closing
opened = binary_closing(binary_opening(anomaly_mask, iterations=1), iterations=1).astype(np.uint8)
text_region3 = opened[35:70, 10:80]
big3 = np.repeat(np.repeat(text_region3 * 255, 12, axis=0), 12, axis=1)
Image.fromarray(big3).save('flag_morphed_12x.png')
print('Saved flag_morphed_12x.png')
