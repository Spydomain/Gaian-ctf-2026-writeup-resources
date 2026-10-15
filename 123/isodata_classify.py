import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

# Load tile: shape (5, 128, 128) = 5 channels, 128 rows, 128 cols
tile = np.load('farm_tile_5channels.npy')
print(f'Tile shape: {tile.shape}')

# Reshape to (128*128, 5) for clustering
pixels = tile.reshape(5, -1).T  # shape (16384, 5)
print(f'Pixels shape: {pixels.shape}')

# Run ISODATA-like clustering (KMeans with 7 classes as per course notes)
kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
labels = kmeans.fit_predict(pixels.astype(float))
class_map = labels.reshape(128, 128)

print(f'\nCluster centers:')
for i, center in enumerate(kmeans.cluster_centers_):
    count = np.sum(labels == i)
    print(f'  Class {i}: {center.astype(int)} ({count} pixels, {count/len(labels)*100:.1f}%)')

# Save class map
colors = np.array([
    [0, 0, 0],       # 0 - black
    [255, 0, 0],     # 1 - red
    [0, 255, 0],     # 2 - green
    [0, 0, 255],     # 3 - blue
    [255, 255, 0],   # 4 - yellow
    [255, 0, 255],   # 5 - magenta
    [0, 255, 255],   # 6 - cyan
], dtype=np.uint8)

class_img = np.zeros((128, 128, 3), dtype=np.uint8)
for i in range(7):
    class_img[class_map == i] = colors[i]
Image.fromarray(class_img).save('isodata_7class.png')
print('\nSaved isodata_7class.png')

# Analyze north field (top half)
print('\n--- North field (rows 0-63) ---')
north_labels = class_map[:64, :].ravel()
for i in range(7):
    count = np.sum(north_labels == i)
    total = np.sum(labels == i)
    pct_in_north = count / total * 100 if total > 0 else 0
    print(f'  Class {i}: {count} pixels in north ({pct_in_north:.1f}% of all class {i})')

# Find the anomalous class - one that's concentrated in north but shouldn't be
# The anomaly is a "patch" so look for a minority class concentrated in north
print('\n--- Looking for anomaly class ---')
from scipy import ndimage

for i in range(7):
    mask = (class_map == i).astype(np.uint8)
    north_mask = mask[:64, :]
    if np.any(north_mask):
        labeled, num = ndimage.label(north_mask)
        sizes = np.bincount(labeled.ravel())[1:]
        print(f'Class {i} in north: {num} components, sizes={sorted(sizes, reverse=True)[:10]}')

# Now let's visualize each class separately
for i in range(7):
    mask = (class_map == i).astype(np.uint8) * 255
    Image.fromarray(mask).save(f'class_{i}_mask.png')
    
    # Also save north field only
    north_mask = mask[:64, :]
    if north_mask.sum() > 0:
        # Scale up 4x for visibility
        big = np.repeat(np.repeat(north_mask, 4, axis=0), 4, axis=1)
        Image.fromarray(big).save(f'class_{i}_north_4x.png')

print('\nSaved individual class masks')
