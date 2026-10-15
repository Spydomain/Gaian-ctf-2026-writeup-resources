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

# The "X-like" pattern appears 3 times in Line 3:
# ###.# / .#### / ..### / ..### / .#### / ###.#
# Inverted:
# ...#. / #.... / ##... / ##... / #.... / ...#.

# This inverted pattern is:
# ...#.    <- gap near right
# #....    <- gap at left  
# ##...    <- gap at left  
# ##...    <- gap at left
# #....    <- gap at left
# ...#.    <- gap near right

# This looks like an HOURGLASS or a character that narrows in the middle
# 'O': .###. / #...# / #...# / #...# / #...# / .###.
# In bold: #...# / .###. / .###. / .###. / .###. / #...#
# Hmm, 'O' bold would have gaps on both sides

# Actually let me look at it again:
# Normal: ###.# / .#### / ..### / ..### / .#### / ###.#
# This has:
# Row 0: full except col 3 (gap at position 3)
# Row 1: full except col 0 (gap at left)
# Row 2: full except cols 0,1 (gap at left)
# Row 3: full except cols 0,1 (gap at left)
# Row 4: full except col 0 (gap at left)
# Row 5: full except col 3 (gap at position 3)

# Inverted (the actual letter shape):
# ...#.   -> only pixel at position 3
# #....   -> only pixel at position 0
# ##...   -> pixels at positions 0,1
# ##...   -> pixels at positions 0,1
# #....   -> only pixel at position 0
# ...#.   -> only pixel at position 3

# This is a DIAGONAL pattern - goes from right (row 0) to left (rows 1-4) back to right (row 5)
# This looks like 'X' viewed through noisy data
# OR it could be '(' or ')' or 'V' or something else

# Let me check if it could be 'O' with one side lost to noise:
# If the right-side gaps were present: ...#. / #...# / ##..# / ##..# / #...# / ...#.
# That would look like an 'O' with extra left pixels. Possible with noise.

# Let me also check: could this be a DIGIT?
# '0': .###. / #...# / #...# / #...# / #...# / .###.
# In bold: #...# / .###. / .###. / .###. / .###. / #...#

# Our pattern vs bold '0':
# ###.# vs #...#  -- very different
# .#### vs .###.  -- close but not exact
# ..### vs .###.  -- close
# ..### vs .###.  -- close  
# .#### vs .###.  -- close
# ###.# vs #...#  -- very different

# What about lowercase letters? 
# In a 5x6 font, lowercase are typically positioned differently

# Let me try brute forcing: generate candidate strings and compare ALL 3 lines
# against the anomaly mask at once

from PIL import Image, ImageFont, ImageDraw
import os

# Let's use the actual font that was used to create this
# The font characteristics from GAIANSPACE:
# - 6 rows high
# - 5 cols wide + 1 gap = 6px pitch
# - BOLD style (letters are mostly filled)

# Since we can't find the exact font, let me try a different approach:
# Use the STRUCTURE of the pattern (which chars repeat, which are unique)

# Line 3 analysis:
# Char 0 = Char 3 = Char 5 (all identical pattern)
# Char 1 = all filled (N?)
# Char 2 = 'I' pattern 
# Char 4 = N-like (mostly filled with bottom gap)

# So Line 3 = X?IX?X} where X is the repeating char and ? are others
# Wait - what if X = a specific letter and the sequence makes a word?
# ?N/HI?N/H?} ... ANINAX? UNIQUE? 

# Let me check: could the repeating char be 'O'?
# OAIOAO} = OAIOAO -> doesn't spell anything
# ONIOO}  - no

# Could it be 'D'?
# DNIDN} - no

# What about numbers? 
# 0NI0N0} = 0NI0N0 -> "onion" with 0s? "0N10N0"?
# Actually... could it be "ONIONS" or "ONION"?

# Let me check 'O' vs our pattern more carefully
# Standard 'O' bold: #...# / .###. / .###. / .###. / .###. / #...#
# Our pattern:       ###.# / .#### / ..### / ..### / .#### / ###.#

# The difference is that our pattern has the gap shifted to the RIGHT
# compared to a centered 'O'. 
# If we shift our pattern 1 pixel to the right:
# .###. / ..### / ...## / ...## / ..### / .###.
# Still not matching

# What if the column alignment is off by 1?
# Let me try col_start + 1 for the "X" chars:
print("=== Testing column offset for X-like chars ===")
for offset in [-2, -1, 0, 1, 2]:
    ci = 0  # first X-char in line 3
    col_start = 24 + offset
    pattern = []
    for r in range(61, 67):
        row = ''.join('#' if anomaly_mask[r, c] else '.' for c in range(col_start, col_start + 5))
        pattern.append(row)
    print(f"  Offset {offset}: ", end="")
    for row in pattern:
        print(row, end=" / ")
    print()

# Let me also check with 5px pitch instead of 6px
print("\n=== Testing 5px pitch for Line 3 ===")
for ci in range(8):
    col_start = 24 + ci * 5
    if col_start + 4 > 127:
        break
    pattern = []
    for r in range(61, 67):
        row = ''.join('#' if anomaly_mask[r, c] else '.' for c in range(col_start, col_start + 5))
        pattern.append(row)
    print(f"  Char {ci} (cols {col_start}-{col_start+4}): ", end="")
    for row in pattern:
        print(row, end=" / ")
    print()

# And try reading all the original pixel data to see if the text is 
# actually encoded differently than binary classification
print("\n=== Raw pixel values in text region ===")
# For Line 3, char 0 (the X-like pattern)
print("Line 3, char 0 raw values (ch3=NIR, ch4=SWIR):")
for r in range(61, 67):
    nir_row = [tile[3, r, c] for c in range(24, 30)]
    swir_row = [tile[4, r, c] for c in range(24, 30)]
    cls_row = [class_map[r, c] for c in range(24, 30)]
    print(f"  r{r}: NIR={nir_row}, SWIR={swir_row}, class={cls_row}")
