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

# The text is clearly visible but noisy. 
# I know from the image: Line 1 = "GAIANSPACE{", Line 2 = "???-CLASS-", Line 3 = "??????}"
# Let me try to match against a 5x6 pixel font by looking at the ASCII art carefully

# Line 1 ASCII art (rows 37-42):
# .####.#####.#####.#######################.#####..###########..###
# ######.####..###...####.#########.########.####.#########.....###
# ###....####..###...####.###########.######.####.###...#####..###.
# ############.###..############..#########.#########...###.....###
# ############.###..##############.######...##################..###
# .##########################.############.###################..###

# Let me try to interpret this as characters with 6px pitch
# Characters at positions: 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 73 (the '{')

# Segment based on the data more carefully
# I know line 1 should be "GAIANSPACE{" = 11 characters
# Total width from col 12 to col 76 = 65 pixels
# 10 chars * 6px + 1 char ('{') * 4px + gap = 64. That fits 6px pitch for first 10 chars

# Let me extract each character and compare against a standard 5x6 font
# Standard Tom Thumb / 4x6 / 5x6 font patterns for uppercase letters

# Using a 5x6 pixel font (columns are bits, MSB at top)
# Standard encoding: each column is a 6-bit value read top-to-bottom
# But our characters are DENSE (mostly #), so this is probably the INVERSE of a standard font

# Actually, let me re-examine. Looking at the original data more carefully:
# The non-anomalous pixels (gaps) form the character shapes
# Let me check if the INVERTED pattern of Line 1 with proper character boundaries gives us readable chars

# First, let me check what "GAIANSPACE" looks like in this font by checking the 
# known first character 'G'

# Character G in most 5x6 fonts:
# .###.
# #...#
# #....
# #.##.
# #..#.
# .###.

# Our char 0 (cols 12-16) NORMAL: 
# .####
# #####
# ###..
# #####
# #####
# .####

# Inverted:
# #....
# .....
# ...##
# .....
# .....
# #....

# That doesn't match either. The text seems to be written in a BOLD/FILLED style.

# Let me try a DIFFERENT approach: use the column density to find character boundaries
# Characters separated by columns with density 0 (empty cols in the anomaly mask)

print("Looking for empty columns in each line:")
for y0, y1, name in [(37, 42, "Line1"), (48, 54, "Line2"), (61, 66, "Line3")]:
    sub = anomaly_mask[y0:y1+1, :]
    col_density = sub.sum(axis=0)
    
    # Find all columns with density 0 (empty)
    empty_cols = [c for c in range(128) if col_density[c] == 0]
    print(f'\n{name}: empty columns = {empty_cols[:30]}...')
    
    # Find groups between empty columns
    groups = []
    in_group = False
    for c in range(128):
        if col_density[c] > 0 and not in_group:
            in_group = True
            start = c
        elif col_density[c] == 0 and in_group:
            in_group = False
            groups.append((start, c-1, c-start))
    if in_group:
        groups.append((start, 127, 128-start))
    
    print(f'{name}: {len(groups)} groups: {[(s,e,w) for s,e,w in groups]}')
    
    # For each group, print the char pattern
    for gi, (s, e, w) in enumerate(groups):
        char = sub[:, s:e+1]
        print(f'\n  Group {gi} (cols {s}-{e}, w={w}):')
        for r in range(char.shape[0]):
            print(f'    {"".join("#" if char[r,c] else "." for c in range(w))}')
