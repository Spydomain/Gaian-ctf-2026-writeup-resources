import re
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
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

# Process 91-byte frames (5 layers, 256 lines each, 85 pixels per line)
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
    
    line = line_high * 16 + line_low_high * 8 + line_low_low  # 0-255
    
    payload = d[4:-2]  # 85 bytes
    
    if len(payload) != 85:
        continue
    
    if layer not in images:
        images[layer] = {}
    images[layer][line] = payload

# Build full 256x85 images for each layer
layer_arrays = []
for layer in range(5):
    img = np.zeros((256, 85), dtype=np.uint8)
    lines_present = 0
    for line in range(256):
        if line in images[layer]:
            img[line, :] = np.frombuffer(images[layer][line], dtype=np.uint8)
            lines_present += 1
        else:
            # Interpolate from neighbors
            prev_line = line - 1
            next_line = line + 1
            while prev_line >= 0 and prev_line not in images[layer]:
                prev_line -= 1
            while next_line < 256 and next_line not in images[layer]:
                next_line += 1
            
            if prev_line >= 0 and next_line < 256:
                # Linear interpolation
                w_prev = next_line - line
                w_next = line - prev_line
                w_total = w_prev + w_next
                img[line, :] = (img[prev_line, :] * w_prev + img[next_line, :] * w_next) / w_total
            elif prev_line >= 0:
                img[line, :] = img[prev_line, :]
            elif next_line < 256:
                img[line, :] = img[next_line, :]
            else:
                img[line, :] = 128
    layer_arrays.append(img)
    print(f'Layer {layer}: {lines_present}/256 lines present')

# Stack as 5-band image (256, 85, 5)
stacked = np.stack(layer_arrays, axis=-1)
print(f'Stacked shape: {stacked.shape}')

# Save each layer as PNG for visual inspection
for layer in range(5):
    Image.fromarray(layer_arrays[layer]).save(f'layer_{layer}_full.png')

# Run ISODATA-like clustering (KMeans with 7 clusters as approximation)
# Reshape to (n_pixels, 5)
pixels = stacked.reshape(-1, 5)
print(f'Total pixels: {pixels.shape[0]}')

# Use KMeans as approximation for ISODATA (7 classes)
kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
labels = kmeans.fit_predict(pixels)
class_map = labels.reshape(256, 85)

print(f'Cluster centers:')
for i, center in enumerate(kmeans.cluster_centers_):
    print(f'  Class {i}: {center}')

# Save class map as image
# Map classes to colors
colors = np.array([
    [0, 0, 0],       # 0 - black
    [255, 0, 0],     # 1 - red
    [0, 255, 0],     # 2 - green
    [0, 0, 255],     # 3 - blue
    [255, 255, 0],   # 4 - yellow
    [255, 0, 255],   # 5 - magenta
    [0, 255, 255],   # 6 - cyan
], dtype=np.uint8)

class_img = colors[class_map]
Image.fromarray(class_img).save('class_map.png')
print('Saved class_map.png')

# Also save grayscale class map
Image.fromarray((class_map * 36).astype(np.uint8)).save('class_map_gray.png')

# Check for anomalies - look at class distribution
print('\nClass distribution:')
for i in range(7):
    count = np.sum(class_map == i)
    print(f'  Class {i}: {count} pixels ({count/class_map.size*100:.1f}%)')

# The "north field" - assuming north is top of image (line 0)
# Check top portion (first 50 lines) for unusual class concentrations
north_region = class_map[:50, :]
print('\nNorth region (lines 0-49) class distribution:')
for i in range(7):
    count = np.sum(north_region == i)
    print(f'  Class {i}: {count} pixels ({count/north_region.size*100:.1f}%)')

# Check if any class is concentrated in a specific area
# Find connected components for each class
from scipy import ndimage

for i in range(7):
    mask = (class_map == i).astype(np.uint8)
    labeled, num_features = ndimage.label(mask)
    if num_features > 0:
        # Find largest component
        component_sizes = np.bincount(labeled.ravel())[1:]  # exclude background 0
        if len(component_sizes) > 0:
            largest = np.max(component_sizes)
            print(f'Class {i}: {num_features} components, largest={largest} pixels')

EOF