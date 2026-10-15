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

anomaly_mask = ((class_map == 3) | (class_map == 5)).astype(np.uint8)

# Process each line
lines_data = [
    (37, 42, "Line 1"),  # rows with actual content (excluding border rows)
    (48, 54, "Line 2"),  # adjusted
    (61, 66, "Line 3"),
]

for y0, y1, name in lines_data:
    sub = anomaly_mask[y0:y1+1, :]
    print(f'\n{"="*60}')
    print(f'{name} (rows {y0}-{y1})')
    print(f'{"="*60}')
    
    # Find columns with pixels
    col_has_pixel = sub.any(axis=0)
    
    # Segment into character blocks (split by empty columns)
    in_char = False
    chars = []
    for c in range(128):
        if col_has_pixel[c] and not in_char:
            in_char = True
            start_c = c
        elif not col_has_pixel[c] and in_char:
            in_char = False
            chars.append((start_c, c))
    if in_char:
        chars.append((start_c, 128))
    
    print(f'Found {len(chars)} character groups:')
    for i, (c0, c1) in enumerate(chars):
        w = c1 - c0
        char_box = sub[:, c0:c1]
        # Print the character
        print(f'\n  Char {i}: cols {c0}-{c1-1}, width={w}')
        for r in range(char_box.shape[0]):
            print(f'    {"".join("#" if char_box[r, c] else "." for c in range(w))}')
    
    # Also identify gaps between character groups
    print(f'\n  Gaps between groups:')
    for i in range(len(chars) - 1):
        gap = chars[i+1][0] - chars[i][1]
        print(f'    Between char {i} and {i+1}: {gap} cols gap')
