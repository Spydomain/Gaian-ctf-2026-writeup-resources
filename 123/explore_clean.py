import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')

# Print raw values for each channel in the text region
# Focus on row 37-42 (line 1 body) and row 49-54 (line 2 body) and row 61-66 (line 3 body)

# Let me look at the class map more carefully with different numbers of classes
# The challenge says ISODATA with 7 classes
pixels = tile.reshape(5, -1).T

# Try the SWIR channel (channel 4) directly
swir = tile[4]  # shape (128, 128)
nir = tile[3]
red = tile[0]
green = tile[1]
blue = tile[2]

# Print SWIR values for line 3 (the unknown)
print("=== SWIR Channel (raw values) for text rows ===")
print("\nLine 3 region (rows 59-68, cols 20-70):")
for r in range(59, 69):
    vals = swir[r, 20:70]
    print(f"  {r}: " + " ".join(f"{v:3d}" for v in vals))

# What if instead of thresholding, we use the ISODATA class map directly?
# The key insight: in ISODATA with 7 classes, some classes correspond to text pixels
# Let me look at the class map for the text region

kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
labels = kmeans.fit_predict(pixels.astype(float))
class_map = labels.reshape(128, 128)

print("\n=== Class labels for text rows ===")
print("\nCluster centers:")
for i, c in enumerate(kmeans.cluster_centers_):
    print(f"  Class {i}: Red={c[0]:.0f} Green={c[1]:.0f} Blue={c[2]:.0f} NIR={c[3]:.0f} SWIR={c[4]:.0f}")

print("\nLine 3 region (rows 59-68, cols 20-70):")
for r in range(59, 69):
    vals = class_map[r, 20:70]
    print(f"  {r}: " + "".join(f"{v}" for v in vals))

# Look at JUST the SWIR channel as a continuous image
# Normalize SWIR to 0-255 for the text region
swir_region = swir[35:70, 10:80].astype(float)
swir_min, swir_max = swir_region.min(), swir_region.max()
print(f"\nSWIR in text region: min={swir_min}, max={swir_max}")

# Normalize and invert for visibility
swir_norm = ((swir_region - swir_min) / (swir_max - swir_min) * 255).astype(np.uint8)
scale = 16
big = np.repeat(np.repeat(swir_norm, scale, axis=0), scale, axis=1)
Image.fromarray(big, mode='L').save('ultra_swir_raw.png')
print("Saved ultra_swir_raw.png")

# Also save the NIR channel raw
nir_region = nir[35:70, 10:80].astype(float)
nir_min, nir_max = nir_region.min(), nir_region.max()
nir_norm = ((nir_region - nir_min) / (nir_max - nir_min) * 255).astype(np.uint8)
big = np.repeat(np.repeat(nir_norm, scale, axis=0), scale, axis=1)
Image.fromarray(big, mode='L').save('ultra_nir_raw.png')
print("Saved ultra_nir_raw.png")

# NIR - SWIR difference
diff = nir.astype(float) - swir.astype(float)
diff_region = diff[35:70, 10:80]
diff_min, diff_max = diff_region.min(), diff_region.max()
diff_norm = ((diff_region - diff_min) / (diff_max - diff_min) * 255).astype(np.uint8)
big = np.repeat(np.repeat(diff_norm, scale, axis=0), scale, axis=1)
Image.fromarray(big, mode='L').save('ultra_nir_swir_diff.png')
print("Saved ultra_nir_swir_diff.png")

# Render the CLASS MAP as a colorized image
# Use distinct colors for each class
colors = [
    (0, 0, 0),      # 0 - black
    (0, 100, 0),     # 1 - dark green  
    (34, 139, 34),   # 2 - forest green
    (255, 255, 0),   # 3 - YELLOW (text class)
    (0, 128, 128),   # 4 - teal
    (255, 0, 0),     # 5 - RED (text class)
    (100, 100, 100), # 6 - gray
]

colored = np.zeros((128, 128, 3), dtype=np.uint8)
for cls_id in range(7):
    mask = (class_map == cls_id)
    for ch in range(3):
        colored[:, :, ch][mask] = colors[cls_id][ch]

region_colored = colored[35:70, 10:80]
big = np.repeat(np.repeat(region_colored, scale, axis=0), scale, axis=1)
Image.fromarray(big).save('ultra_class_colored.png')
print("Saved ultra_class_colored.png")

# Also try: use the SWIR delta approach but with a much higher threshold
red_f = tile[0].astype(float)
swir_f = tile[4].astype(float)
expected_swir = np.where(red_f < 25, 48.0, 97.0)
swir_delta = np.abs(swir_f - expected_swir)

# Render swir_delta as continuous image
delta_region = swir_delta[35:70, 10:80]
delta_norm = ((delta_region) / delta_region.max() * 255).astype(np.uint8)
big = np.repeat(np.repeat(delta_norm, scale, axis=0), scale, axis=1)
Image.fromarray(big, mode='L').save('ultra_swir_delta_continuous.png')
print("Saved ultra_swir_delta_continuous.png")

# Try different thresholds on the SWIR delta
for thresh in [15, 20, 25, 30, 35, 40, 50]:
    mask = (swir_delta > thresh).astype(np.uint8)
    region = mask[35:70, 10:80]
    on_pixels = region.sum()
    total = region.shape[0] * region.shape[1]
    pct = on_pixels / total * 100
    print(f"  Threshold {thresh}: {on_pixels}/{total} = {pct:.1f}%")

# Try the gradient magnitude to find edges of text
from scipy import ndimage
# Gradient of SWIR channel  
grad_y = ndimage.sobel(swir.astype(float), axis=0)
grad_x = ndimage.sobel(swir.astype(float), axis=1)
grad = np.sqrt(grad_x**2 + grad_y**2)
grad_region = grad[35:70, 10:80]
grad_norm = ((grad_region - grad_region.min()) / (grad_region.max() - grad_region.min()) * 255).astype(np.uint8)
big = np.repeat(np.repeat(grad_norm, scale, axis=0), scale, axis=1)
Image.fromarray(big, mode='L').save('ultra_swir_gradient.png')
print("Saved ultra_swir_gradient.png")
