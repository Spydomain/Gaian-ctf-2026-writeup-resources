import numpy as np
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')
# Shape: (5, 128, 128)

# Look at the individual channels in the text region
# The channels are likely B, G, R, NIR, SWIR based on the course notes
# Channel 3 (NIR) and Channel 4 (SWIR) are likely to show the anomaly best

# Let's visualize each channel in the text region at high resolution
for ch in range(5):
    ch_data = tile[ch, 35:70, 10:80]
    # Normalize to 0-255
    ch_norm = ((ch_data - ch_data.min()) / (ch_data.max() - ch_data.min() + 0.001) * 255).astype(np.uint8)
    big = np.repeat(np.repeat(ch_norm, 12, axis=0), 12, axis=1)
    Image.fromarray(big).save(f'flag_ch{ch}_12x.png')

# The text might be most visible in a combination
# NDVI = (NIR - R) / (NIR + R) 
nir = tile[3].astype(float)
red = tile[2].astype(float)
ndvi = (nir - red) / (nir + red + 0.001)

# Normalize to 0-255
ndvi_region = ndvi[35:70, 10:80]
ndvi_norm = ((ndvi_region - ndvi_region.min()) / (ndvi_region.max() - ndvi_region.min() + 0.001) * 255).astype(np.uint8)
big = np.repeat(np.repeat(ndvi_norm, 12, axis=0), 12, axis=1)
Image.fromarray(big).save('flag_ndvi_12x.png')

# Also try: difference between NIR and SWIR
swir = tile[4].astype(float)
diff = np.abs(nir - swir)
diff_region = diff[35:70, 10:80]
diff_norm = ((diff_region - diff_region.min()) / (diff_region.max() - diff_region.min() + 0.001) * 255).astype(np.uint8)
big = np.repeat(np.repeat(diff_norm, 12, axis=0), 12, axis=1)
Image.fromarray(big).save('flag_nir_swir_diff_12x.png')

# Another approach: use PCA to find the principal component that shows the text
from sklearn.decomposition import PCA
text_pixels = tile[:, 35:70, 10:80].reshape(5, -1).T  # (N, 5)
pca = PCA(n_components=5)
pca_transformed = pca.fit_transform(text_pixels.astype(float))
print('PCA explained variance:', pca.explained_variance_ratio_)

for comp in range(5):
    pc = pca_transformed[:, comp].reshape(35, 70)
    pc_norm = ((pc - pc.min()) / (pc.max() - pc.min() + 0.001) * 255).astype(np.uint8)
    big = np.repeat(np.repeat(pc_norm, 12, axis=0), 12, axis=1)
    Image.fromarray(big).save(f'flag_pc{comp}_12x.png')

print('Saved all channel/transform visualizations')
