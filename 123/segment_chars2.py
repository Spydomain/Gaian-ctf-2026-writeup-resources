import numpy as np
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')
pixels = tile.reshape(5, -1).T
kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
labels = kmeans.fit_predict(pixels.astype(float))
class_map = labels.reshape(128, 128)
anomaly_mask = ((class_map == 3) | (class_map == 5)).astype(np.uint8)

# Characters are 5 or 6 pixels wide typically in a pixel font
# Let me look at column density to find character boundaries

lines_data = [
    (37, 42, "Line 1", 12, 77),
    (48, 54, "Line 2", 15, 75),
    (61, 66, "Line 3", 24, 65),
]

for y0, y1, name, c_start, c_end in lines_data:
    sub = anomaly_mask[y0:y1+1, c_start:c_end]
    h, w = sub.shape
    
    print(f'\n{"="*60}')
    print(f'{name} (rows {y0}-{y1}, cols {c_start}-{c_end})')
    print(f'{"="*60}')
    
    # Column density
    col_density = sub.sum(axis=0)
    density_str = ''
    for c in range(w):
        density_str += str(col_density[c])
    print(f'Column density: {density_str}')
    
    # Print the pattern
    for r in range(h):
        print(''.join('#' if sub[r, c] else '.' for c in range(w)))
    
    # Try to identify 5-pixel wide characters
    # In a standard 5x7 pixel font, characters are 5 wide with 1 pixel gap
    # Let's try splitting every 6 pixels (5 char + 1 gap)
    print(f'\nAssuming 5px wide chars with 1px gap (6px pitch):')
    num_chars = w // 6 + 1
    result = ''
    for i in range(0, w, 6):
        char_cols = sub[:, i:min(i+5, w)]
        if char_cols.shape[1] < 3:
            continue
        # Convert to binary pattern for matching
        pattern = []
        for r in range(char_cols.shape[0]):
            row_val = 0
            for c in range(char_cols.shape[1]):
                if char_cols[r, c]:
                    row_val |= (1 << (4 - c))
            pattern.append(row_val)
        # Print the char
        print(f'\n  Char at col {c_start + i}:')
        for r in range(char_cols.shape[0]):
            print(f'    {"".join("#" if char_cols[r, c] else "." for c in range(char_cols.shape[1]))}')
