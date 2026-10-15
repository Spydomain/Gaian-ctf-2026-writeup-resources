import numpy as np
from PIL import Image

# Load the 5-channel farm tile
tile = np.load('farm_tile_5channels.npy')
print(f'Tile shape: {tile.shape}')
print(f'Tile dtype: {tile.dtype}')
print(f'Min/max per channel:')
for ch in range(tile.shape[2]):
    print(f'  Ch{ch}: min={tile[:,:,ch].min()}, max={tile[:,:,ch].max()}, mean={tile[:,:,ch].mean():.1f}')

# The anomaly detection logic from previous work: NIR > 90 and SWIR > 75
# Channels are likely: R, G, B, NIR, SWIR (indices 0-4)
nir = tile[:,:,3].astype(float)
swir = tile[:,:,4].astype(float)

# Try multiple anomaly detection approaches
print('\n--- Anomaly Detection ---')

# Approach 1: NIR > 90 and SWIR > 75
mask1 = (nir > 90) & (swir > 75)
print(f'NIR>90 & SWIR>75: {mask1.sum()} pixels')

# Approach 2: Look at the actual anomaly region more carefully
# Show where the anomaly pixels are
rows, cols = np.where(mask1)
if len(rows) > 0:
    print(f'Anomaly region: rows {rows.min()}-{rows.max()}, cols {cols.min()}-{cols.max()}')

# Let's also look at the entire north field region
# and try ISODATA (iterative self-organizing) classification
# But first, let's look at raw pixel values in the anomaly patch

# Extract the anomaly region
if len(rows) > 0:
    r_min, r_max = rows.min(), rows.max()
    c_min, c_max = cols.min(), cols.max()
    patch = tile[r_min:r_max+1, c_min:c_max+1, :]
    print(f'\nAnomaly patch shape: {patch.shape}')
    
    # Print the anomaly mask as text (binary image)
    patch_mask = mask1[r_min:r_max+1, c_min:c_max+1]
    print(f'\nAnomaly mask ({patch_mask.shape}):')
    for row in range(patch_mask.shape[0]):
        line = ''
        for col in range(patch_mask.shape[1]):
            line += '#' if patch_mask[row, col] else '.'
        print(line)

# Try different thresholds
print('\n--- Different thresholds ---')
for nir_thresh in [80, 85, 90, 95, 100]:
    for swir_thresh in [60, 65, 70, 75, 80]:
        mask = (nir > nir_thresh) & (swir > swir_thresh)
        count = mask.sum()
        if 50 < count < 2000:
            print(f'NIR>{nir_thresh} & SWIR>{swir_thresh}: {count} pixels')

# Try looking at individual channels for anomalies
print('\n--- Single channel thresholds (north half) ---')
north = tile[:tile.shape[0]//2, :, :]
for ch in range(5):
    ch_data = north[:,:,ch].astype(float)
    mean = ch_data.mean()
    std = ch_data.std()
    # Pixels more than 2 std from mean
    mask_high = ch_data > (mean + 2*std)
    mask_low = ch_data < (mean - 2*std)
    print(f'Ch{ch}: mean={mean:.1f}, std={std:.1f}, high_outliers={mask_high.sum()}, low_outliers={mask_low.sum()}')

# Try NDVI-based anomaly (if ch0=R, ch3=NIR)
print('\n--- NDVI anomaly ---')
red = tile[:,:,0].astype(float) + 0.001
ndvi = (nir - red) / (nir + red + 0.001)
ndvi_north = ndvi[:tile.shape[0]//2, :]
print(f'NDVI north: min={ndvi_north.min():.3f}, max={ndvi_north.max():.3f}, mean={ndvi_north.mean():.3f}')

# Anomaly: places where NDVI differs significantly
ndvi_mean = ndvi_north.mean()
ndvi_std = ndvi_north.std()
ndvi_anom = np.abs(ndvi_north - ndvi_mean) > 2 * ndvi_std
print(f'NDVI anomaly pixels (north): {ndvi_anom.sum()}')

# Save a high-res version of the anomaly text
if len(rows) > 0:
    # Scale up the mask for better readability
    scale = 10
    big_mask = np.repeat(np.repeat(patch_mask.astype(np.uint8) * 255, scale, axis=0), scale, axis=1)
    Image.fromarray(big_mask).save('flag_text_10x.png')
    print('\nSaved flag_text_10x.png')
    
    # Also try inverting
    Image.fromarray(255 - big_mask).save('flag_text_10x_inv.png')
    print('Saved flag_text_10x_inv.png')
