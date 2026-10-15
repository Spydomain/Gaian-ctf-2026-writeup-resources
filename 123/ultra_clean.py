import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from sklearn.cluster import KMeans
from scipy import ndimage
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')
# tile shape: (5, 128, 128)

# ====== METHOD 1: SWIR DELTA (best method from previous analysis) ======
red = tile[0].astype(float)
swir = tile[4].astype(float)

# Background SWIR depends on red channel value
expected_swir = np.where(red < 25, 48.0, 97.0)
swir_delta = np.abs(swir - expected_swir)
text_mask_swir = (swir_delta > 25).astype(np.uint8)

# ====== METHOD 2: KMeans class 3 | class 5 ======
pixels = tile.reshape(5, -1).T
kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
labels = kmeans.fit_predict(pixels.astype(float))
class_map = labels.reshape(128, 128)
text_mask_km = ((class_map == 3) | (class_map == 5)).astype(np.uint8)

# ====== METHOD 3: Combined vote - SWIR delta + KMeans ======
combined = ((text_mask_swir + text_mask_km) >= 1).astype(np.uint8)

# ====== METHOD 4: Strict intersection ======
strict = ((text_mask_swir + text_mask_km) >= 2).astype(np.uint8)

# ====== METHOD 5: Channel-based: NIR/SWIR ratio anomaly ======
nir = tile[3].astype(float)
ratio = np.where(swir > 0, nir / (swir + 0.1), 0)
# Normalize
ratio_norm = (ratio - ratio.min()) / (ratio.max() - ratio.min())

# ====== METHOD 6: PCA on text region ======
from sklearn.decomposition import PCA
text_pixels = tile[:, 35:70, 10:80].reshape(5, -1).T
pca = PCA(n_components=1)
pc1 = pca.fit_transform(text_pixels.astype(float))
pc1_img = pc1.reshape(35, 70)
pc1_norm = ((pc1_img - pc1_img.min()) / (pc1_img.max() - pc1_img.min()) * 255).astype(np.uint8)

# Print raw text patterns for manual reading
print("=== RAW SWIR DELTA TEXT (rows 35-70, cols 0-127) ===")
for mask_name, mask in [("SWIR_DELTA", text_mask_swir), ("KMEANS", text_mask_km), ("STRICT", strict)]:
    print(f"\n--- {mask_name} ---")
    for r in range(35, 70):
        line = ''
        for c in range(128):
            line += '█' if mask[r, c] else ' '
        stripped = line.rstrip()
        if '█' in stripped:
            print(f'{r:3d}|{stripped}')

# Save multiple versions at high res
scale = 16
for mask_name, mask in [("swir_delta", text_mask_swir), ("kmeans", text_mask_km), 
                          ("combined", combined), ("strict", strict)]:
    region = mask[35:70, 10:80]
    big = np.repeat(np.repeat(region * 255, scale, axis=0), scale, axis=1)
    img = Image.fromarray(big, mode='L')
    img.save(f'ultra_{mask_name}_{scale}x.png')
    print(f'Saved ultra_{mask_name}_{scale}x.png')

# Save PCA version
big_pca = np.repeat(np.repeat(pc1_norm, scale, axis=0), scale, axis=1)
img_pca = Image.fromarray(big_pca, mode='L')
img_pca.save(f'ultra_pca_{scale}x.png')
print(f'Saved ultra_pca_{scale}x.png')

# Save NIR/SWIR ratio
region_ratio = ratio_norm[35:70, 10:80]
region_ratio_u8 = (region_ratio * 255).astype(np.uint8)
big_ratio = np.repeat(np.repeat(region_ratio_u8, scale, axis=0), scale, axis=1)
img_ratio = Image.fromarray(big_ratio, mode='L')
img_ratio.save(f'ultra_ratio_{scale}x.png')
print(f'Saved ultra_ratio_{scale}x.png')

# ====== BEST: Anti-aliased scaled version of SWIR delta ======
# Use PIL resize with NEAREST for pixel art, then apply slight smoothing
region = text_mask_swir[35:70, 10:80]
img_small = Image.fromarray(region * 255, mode='L')
# Scale using NEAREST first (preserve sharp pixels)
w, h = region.shape[1], region.shape[0]
img_big = img_small.resize((w * scale, h * scale), Image.NEAREST)
img_big.save('ultra_best_nearest.png')

# Also try bicubic for smoother look
img_smooth = img_small.resize((w * scale, h * scale), Image.BICUBIC)
# Apply threshold to re-binarize
arr_smooth = np.array(img_smooth)
arr_binary = (arr_smooth > 128).astype(np.uint8) * 255
Image.fromarray(arr_binary, mode='L').save('ultra_best_smooth.png')
print('Saved ultra_best_smooth.png')

# ====== Individual line images, super high res for close inspection ======
scale2 = 24
lines_info = [
    ("line1", 36, 44, 10, 80),
    ("line2", 47, 56, 10, 80),
    ("line3", 59, 68, 20, 70),
]

for name, y0, y1, x0, x1 in lines_info:
    region = text_mask_swir[y0:y1, x0:x1]
    big = np.repeat(np.repeat(region * 255, scale2, axis=0), scale2, axis=1)
    img = Image.fromarray(big, mode='L')
    img.save(f'ultra_{name}_{scale2}x.png')
    print(f'Saved ultra_{name}_{scale2}x.png ({big.shape})')
    
    # Print ASCII art
    print(f'\n  {name} ASCII ({y0}-{y1}, cols {x0}-{x1}):')
    for r in range(y0, y1):
        line = ''
        for c in range(x0, x1):
            line += '█' if text_mask_swir[r, c] else '·'
        print(f'  {r}: {line}')

# ====== Also try: Use all 5 channels as a false color image ======
# Channel 0=Red, 1=Green, 2=Blue, 3=NIR, 4=SWIR
# False color: NIR as Red, Red as Green, Green as Blue
fc = np.zeros((128, 128, 3), dtype=np.uint8)
fc[:, :, 0] = tile[3]  # NIR -> R
fc[:, :, 1] = tile[0]  # Red -> G  
fc[:, :, 2] = tile[1]  # Green -> B
region_fc = fc[35:70, 10:80]
big_fc = np.repeat(np.repeat(region_fc, scale, axis=0), scale, axis=1)
Image.fromarray(big_fc).save('ultra_false_color.png')
print('Saved ultra_false_color.png')

print("\nDone! Check the ultra_*.png files")
