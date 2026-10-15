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

# The anomalous classes are 3 and 5 - they form the BACKGROUND of the text
# The text itself is carved out as NON-anomalous pixels within the anomaly region
anomaly_mask = ((class_map == 3) | (class_map == 5)).astype(np.uint8)

# INVERT: text = non-anomalous pixels within the anomaly bounding box
# But we need to be smarter - only invert within the text region

# Line 1: rows 37-42, cols 12-76
# Line 2: rows 48-54, cols 15-75 
# Line 3: rows 61-66, cols 24-64

lines_data = [
    (37, 42, "Line 1", 12, 77),
    (48, 54, "Line 2", 15, 75),
    (61, 66, "Line 3", 24, 65),
]

# Actually wait - looking again, the patterns WITH the 6px pitch look very dense
# Let me try INVERTING - maybe the text is in the GAPS
for y0, y1, name, c_start, c_end in lines_data:
    sub = anomaly_mask[y0:y1+1, c_start:c_end]
    inv = 1 - sub  # invert
    h, w = inv.shape
    
    print(f'\n{"="*60}')
    print(f'{name} INVERTED (rows {y0}-{y1}, cols {c_start}-{c_end})')
    print(f'{"="*60}')
    
    # Print inverted
    for r in range(h):
        print(''.join('#' if inv[r, c] else '.' for c in range(w)))
    
    # Column density
    col_density = inv.sum(axis=0)
    density_str = ''
    for c in range(w):
        density_str += str(col_density[c])
    print(f'Column density: {density_str}')
    
    # Now try 5px pitch
    print(f'\nAssuming 5px wide chars with 1px gap:')
    
    # Find character boundaries using column density
    col_has_pixel = inv.any(axis=0)
    in_char = False
    chars = []
    for c in range(w):
        if col_has_pixel[c] and not in_char:
            in_char = True
            start_c = c
        elif not col_has_pixel[c] and in_char:
            in_char = False
            chars.append((start_c, c))
    if in_char:
        chars.append((start_c, w))
    
    print(f'  Found {len(chars)} character groups:')
    for i, (c0, c1) in enumerate(chars):
        char_w = c1 - c0
        char_box = inv[:, c0:c1]
        print(f'\n  Group {i}: cols {c_start+c0}-{c_start+c1-1}, width={char_w}')
        for r in range(h):
            print(f'    {"".join("#" if char_box[r, c] else "." for c in range(char_w))}')

# Save inverted version
text_mask = np.zeros((128, 128), dtype=np.uint8)
for y0, y1, name, c_start, c_end in lines_data:
    sub = anomaly_mask[y0:y1+1, c_start:c_end]
    text_mask[y0:y1+1, c_start:c_end] = 1 - sub

# Scale up 8x
text_region = text_mask[35:69, :]
big = np.repeat(np.repeat(text_region * 255, 8, axis=0), 8, axis=1)
Image.fromarray(big).save('flag_text_inverted_8x.png')
print('\nSaved flag_text_inverted_8x.png')
