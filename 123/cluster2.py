import re
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from scipy import ndimage
import warnings
warnings.filterwarnings('ignore')

# Parse frames from all_frames.txt
frames = []
with open('all_frames.txt', 'r') as f:
    lines = f.readlines()

i = 0
while i < len(lines):
    line = lines[i].strip()
    if line.startswith('FRAME:'):
        m = re.match(r'FRAME: len=(\d+), phy_crc_ok=(\d+), app_crc_ok=(\d+), app_crc=([0-9a-f]+)/([0-9a-f]+)', line)
        if m:
            length = int(m.group(1))
            if i + 1 < len(lines):
                hex_line = lines[i + 1].strip()
                hex_bytes = hex_line.split()
                if len(hex_bytes) == length:
                    data = bytes(int(b, 16) for b in hex_bytes)
                    frames.append({
                        'length': length,
                        'data': data
                    })
                    i += 1
    i += 1

# Process 91-byte frames (5 layers, lines 112-367, 85 pixels per line)
frames_91 = [f for f in frames if f['length'] == 91]

layer_map = {0x34: 0, 0x44: 1, 0x54: 2, 0x64: 3, 0x74: 4}

images = {}
for f in frames_91:
    d = f['data']
    b0, b1, b2 = d[0], d[1], d[2]
    
    if b0 not in layer_map:
        continue
    layer = layer_map[b0]
    
    line_high = (b1 >> 4) & 0xF  # 0-15
    line_low_high = (b2 >> 4) & 0xF  # 0xE or 0xF -> 0 or 1
    line_low_low = b2 & 0xF  # 0-7
    
    # Line number in full image: 112-367
    line_full = (line_high + 7) * 16 + line_low_high * 8 + line_low_low
    # Convert to 0-255 index for our array
    line_idx = line_full - 112  # 0-255
    
    payload = d[4:-2]  # 85 bytes
    
    if len(payload) != 85:
        continue
    
    if layer not in images:
        images[layer] = {}
    images[layer][line_idx] = payload

# Build full 256x85 images for each layer (lines 0-255 correspond to full lines 112-367)
layer_arrays = []
for layer in range(5):
    img = np.zeros((256, 85), dtype=np.uint8)
    lines_present = 0
    for line_idx in range(256):
        if line_idx in images[layer]:
            img[line_idx, :] = np.frombuffer(images[layer][line_idx], dtype=np.uint8)
            lines_present += 1
        else:
            # Interpolate from neighbors
            prev_line = line_idx - 1
            next_line = line_idx + 1
            while prev_line >= 0 and prev_line not in images[layer]:
                prev_line -= 1
            while next_line < 256 and next_line not in images[layer]:
                next_line += 1
            
            if prev_line >= 0 and next_line < 256:
                w_prev = next_line - line_idx
                w_next = line_idx - prev_line
                w_total = w_prev + w_next
                img[line_idx, :] = (img[prev_line, :] * w_prev + img[next_line, :] * w_next) / w_total
            elif prev_line >= 0:
                img[line_idx, :] = img[prev_line, :]
            elif next_line < 256:
                img[line_idx, :] = img[next_line, :]
            else:
                img[line_idx, :] = 128
    layer_arrays.append(img)
    print(f'Layer {layer}: {lines_present}/256 lines present')

# Stack as 5-band image (256, 85, 5)
stacked = np.stack(layer_arrays, axis=-1)
print(f'Stacked shape: {stacked.shape}')

# Save each layer as PNG for visual inspection
for layer in range(5):
    Image.fromarray(layer_arrays[layer]).save(f'layer_{layer}_full.png')

# Run KMeans clustering (7 classes) on valid pixels only (non-interpolated)
# Create mask of valid pixels
valid_mask = np.zeros((256, 85), dtype=bool)
for layer in range(5):
    for line_idx in images[layer]:
        valid_mask[line_idx, :] = True

print(f'Valid pixels: {valid_mask.sum()} / {256*85}')

# Extract valid pixels
valid_pixels = stacked[valid_mask]
print(f'Valid pixel shape: {valid_pixels.shape}')

# Run KMeans with 7 clusters
kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
valid_labels = kmeans.fit_predict(valid_pixels)

# Create full class map
class_map = np.full((256, 85), -1, dtype=np.int32)
class_map[valid_mask] = valid_labels

print(f'Cluster centers:')
for i, center in enumerate(kmeans.cluster_centers_):
    print(f'  Class {i}: {center}')

# Save class map as image
colors = np.array([
    [0, 0, 0],       # 0
    [255, 0, 0],     # 1
    [0, 255, 0],     # 2
    [0, 0, 255],     # 3
    [255, 255, 0],   # 4
    [255, 0, 255],   # 5
    [0, 255, 255],   # 6
], dtype=np.uint8)

# Map -1 (invalid) to gray
class_img = np.zeros((256, 85, 3), dtype=np.uint8)
for i in range(7):
    class_img[class_map == i] = colors[i]
class_img[class_map == -1] = [128, 128, 128]
Image.fromarray(class_img).save('class_map_valid.png')
print('Saved class_map_valid.png')

# Class distribution in valid region
print('\nClass distribution (valid pixels only):')
for i in range(7):
    count = np.sum(valid_labels == i)
    print(f'  Class {i}: {count} pixels ({count/len(valid_labels)*100:.1f}%)')

# Analyze north region (first 50 lines of transmitted region = lines 0-49 in our array = full lines 112-161)
north_region_mask = valid_mask[:50, :]
north_labels = class_map[:50, :][north_region_mask]
print('\nNorth region (lines 0-49, full lines 112-161) class distribution:')
for i in range(7):
    count = np.sum(north_labels == i)
    total = len(north_labels)
    if total > 0:
        print(f'  Class {i}: {count} pixels ({count/total*100:.1f}%)')

# Check for anomalies - look for small clusters or unusual patterns
# Find connected components for each class in valid region
for i in range(7):
    mask = (class_map == i).astype(np.uint8)
    labeled, num_features = ndimage.label(mask)
    if num_features > 0:
        component_sizes = np.bincount(labeled.ravel())[1:]
        if len(component_sizes) > 0:
            largest = np.max(component_sizes)
            print(f'Class {i}: {num_features} components, largest={largest} pixels')

# Look at the north region more carefully - find any class that appears only there
print('\nClasses appearing in north region:')
north_classes = set(north_labels)
all_classes = set(valid_labels)
for c in north_classes:
    # What fraction of this class is in north region?
    total_c = np.sum(valid_labels == c)
    north_c = np.sum(north_labels == c)
    print(f'  Class {c}: {north_c}/{total_c} ({north_c/total_c*100:.1f}% in north)')

# The anomaly might be a small patch of a rare class in the north
# Check each class for spatial concentration in north
for i in range(7):
    mask = (class_map == i)
    north_mask = mask[:50, :]
    if np.any(north_mask):
        # Find connected components in north
        labeled_n, num_n = ndimage.label(north_mask.astype(np.uint8))
        if num_n > 0:
            sizes_n = np.bincount(labeled_n.ravel())[1:]
            print(f'  Class {i} in north: {num_n} components, sizes={sizes_n}')

EOF