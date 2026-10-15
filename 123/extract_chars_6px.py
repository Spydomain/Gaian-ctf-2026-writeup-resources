import numpy as np
from PIL import Image, ImageFont, ImageDraw
from sklearn.cluster import KMeans
import itertools
import warnings
warnings.filterwarnings('ignore')

# Load and classify
tile = np.load('farm_tile_5channels.npy')
pixels = tile.reshape(5, -1).T
kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
labels = kmeans.fit_predict(pixels.astype(float))
class_map = labels.reshape(128, 128)
anomaly_mask = ((class_map == 3) | (class_map == 5)).astype(np.uint8)

# Instead of font matching, let's think about what the flag text says
# We can see 3 lines of text in the anomaly map:

# Line 1 (rows 37-42, cols 12-76): GAIANSPACE{
# Line 2 (rows 48-54, cols 15-74): ???-?????- (10 chars at 6px = 60px) 
# Line 3 (rows 61-66, cols 24-64): ???????} (41px, so ~7 chars)

# Looking at the zoomed images carefully:
# Line 1: G A I A N S P A C E {  -- this is confirmed
# Line 2: Looks like "7th-CLASS-" or "THE-CLASS-" 
# Line 3: Something + "}"

# The challenge mentions "7 classes" in the ISODATA course notes
# And "count what actually grows here"
# So the flag likely references the classification

# From the images and pixel patterns, Line 2 starts with something,
# followed by -CLASS-

# Let me look at Line 2 more carefully
# Line 2 starts with 3 chars before first '-', then 'CLASS', then '-'
# The first group before '-' at cols 15-32:
# Rows 48-54:
#   ######......
#   ###################
#   ...###############
#   ..###..###..######
#   ..###..###..######
#   .###...###..######
#   .###..#############

# Hmm, let me look at this as 6px-wide characters
# Char 0 (cols 15-20): first 6 columns of line 2
# Char 1 (cols 21-26)
# Char 2 (cols 27-32)
# Then '-' at cols 33-38
# Then CLASS at cols 39-68 (5 chars * 6 = 30)
# Then '-' at cols 69-74

print("Line 2 characters at 6px pitch:")
for ci, col_start in enumerate(range(15, 75, 6)):
    col_end = min(col_start + 5, 74)
    w = col_end - col_start + 1
    if w < 3:
        break
    print(f"\nChar {ci} (cols {col_start}-{col_end}):")
    for r in range(48, 55):
        print(f"  {''.join('#' if anomaly_mask[r, c] else '.' for c in range(col_start, col_end+1))}")

print("\n\nLine 3 characters at 6px pitch:")
for ci, col_start in enumerate(range(24, 65, 6)):
    col_end = min(col_start + 5, 64)
    w = col_end - col_start + 1
    if w < 3:
        break
    print(f"\nChar {ci} (cols {col_start}-{col_end}):")
    for r in range(61, 67):
        print(f"  {''.join('#' if anomaly_mask[r, c] else '.' for c in range(col_start, col_end+1))}")

# Also try Line 1 to validate the 6px pitch
print("\n\nLine 1 characters at 6px pitch (should be GAIANSPACE):")
for ci, col_start in enumerate(range(12, 72, 6)):
    col_end = col_start + 5
    print(f"\nChar {ci} (cols {col_start}-{col_end}):")
    for r in range(37, 43):
        print(f"  {''.join('#' if anomaly_mask[r, c] else '.' for c in range(col_start, col_end+1))}")
