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

# Define a complete 5x6 bold pixel font
# These are the BOLD patterns where letters are carved out of a filled block
# Pattern format: each row is 5 chars, '#' = filled, '.' = gap that forms the letter

# First, let me study the INVERTED patterns from the known GAIANSPACE chars
# Then build patterns for all possible characters

# Known character INVERTED patterns from Line 1:
# G: #....  / .....  / ...## / ..... / ..... / #....
# A: ..... / #.... / #.... / ..... / ..... / .....
# I: ..... / #...# / #...# / #...# / #...# / .....
# N: ..... / ..... / ..... / ..... / ..... / ...#.
# S: ..... / ...#. / ..... / ##... / ..#.. / .....
# P: ..... / ..... / ..... / ..... / ...## / ....#
# C: #.... / ..... / ...## / ...## / ..... / .....
# E: ..... / ...## / ..... / ...## / ..... / .....

# So in NORMAL (non-inverted), the patterns are:
# G: .####  / ##### / ###.. / ##### / ##### / .####
# A: ##### / .#### / .#### / ##### / ##### / #####
# I: ##### / .###. / .###. / .###. / .###. / #####
# N: ##### / ##### / ##### / ##### / ##### / ###.#
# S: ##### / ###.# / ##### / ..### / ##.## / #####
# P: ##### / ##### / ##### / ##### / ###.. / ####.
# C: .#### / ##### / ###.. / ###.. / ##### / #####
# E: ##### / ###.. / ##### / ###.. / ##### / #####

# Looking at the unknown chars:
# Line 2, Char 0: #####/#####/...##/..###/.###./.###.  -- This is '7'
#   Inverted:     ...../...../##.../##.../....#/....#
#   A '7' would be: ###.. / ...#. / ..#.. / .#... / .#... / .#...
#   In bold/inverted: .#### / #####/ ##### / ####. / ####. / ####.
#   Hmm, not quite matching. Let me look at this differently.

# Actually, the pattern for char 0 of line 2 looks like '7' (or 'T'):
# .####.  <- top bar with gap at left
# ######  <- full
# ...###  <- right side only (descending)  
# ..###.  <- descending
# .###..  <- descending
# .###..  <- descending
# This looks like a '7' rotated/slanted - diagonal from upper-right to lower-left

# Char 3 of line 2 (cols 33-37) is clearly '-' (hyphen):
# #....  (almost all blank)
# .....
# #####  (full bar in middle)
# .....
# .....
# #....

# Char 9 of line 2 (cols 69-73) is also '-':
# .....
# .....
# #####
# .....
# .....
# .....

# So Line 2 structure is: ???-?????-
# Which means 3 chars, hyphen, 5 chars, hyphen

# Chars 4-8 (between hyphens) with high confidence:
# Char 4: C (97% match)
# Char 5: 'L' maybe? Let me check: ####./###../###../###../#####/#####
#   Inverted: ....#/...##/...##/...##/...../...... 
#   This looks like 'L' (vertical bar with bottom horizontal) in bold style
# Char 6: A (100% match)
# Char 7: S (97% match)
# Char 8: S (97% match)

# So the word between hyphens is probably: C L A S S -> "CLASS"

# Now for chars 0-2 of Line 2:
# Char 0: #####/...##/..###/..###/.###./.###. 
#   Pattern goes from right to left as you go down - this is a '7'
# Char 1: I (93% match) -> not I, let me look again:
#   ##### / ##### / .###. / .###. / .###. / #####
#   This IS 'I' - but could also be 'T' if the bottom is different
#   Actually: top full, then narrow middle, bottom full = 'I' 
#   But wait - could this be 'T'? 'T' would be full top, narrow rest, no bottom bar
#   Our char has BOTH top and bottom bars = definitely 'I' or 'H'

# Wait, let me reconsider. Looking at these carefully:
# Char 0 Line2: descending diagonal = '7'
# Char 1 Line2: ##### / ##### / .###. / .###. / .###. / ##### = probably 'I'  
# But wait, this has 7 rows not 6. Line 2 is rows 48-54 = 7 rows!

# Let me re-examine - Line 2 has 7 rows (48-54), not 6
# Row 48 is the padding/top border of the font

# Let me redo with proper row range:

print("=== Re-examining with corrected row ranges ===\n")

# Line 1: 8 total rows (36-43), actual content rows 37-42 (6 rows)
# Line 2: 7 total rows (48-54), row 48 might be extra
# Line 3: 6 total rows (61-66)

# For Line 2, let me check what row 48 looks like:
print("Line 2, row 48:")
line = ''.join('#' if anomaly_mask[48, c] else '.' for c in range(128))
print(line.rstrip('.'))

# It shows: ...............######
# That's just the top of char 0 (the '7')
# So the '7' character actually uses 7 rows: 48-54

# OK, so the font might be 7 rows tall (5x7), not 6
# Let me check Line 1 more carefully:
print("\nLine 1, rows 36-43:")
for r in range(36, 44):
    line = ''.join('#' if anomaly_mask[r, c] else '.' for c in range(10, 80))
    print(f"  {r}: {line}")

# Row 36 and 43 are the { borders
# So the actual font is 6 rows (37-42) for line 1, but 7 rows (48-54) for line 2?
# That's inconsistent. Let me check if line 2 char 0 is actually a 7-row character

# For consistency, let me use rows that match for all lines:
# Line 1: rows 37-42 (6 rows)
# Line 2: rows 49-54 (6 rows, skipping the top padding row 48)
# Line 3: rows 61-66 (6 rows)

print("\n=== Corrected Line 2 (rows 49-54) at 6px pitch ===\n")
for ci in range(10):
    col_start = 15 + ci * 6
    pattern = []
    for r in range(49, 55):
        row = ''
        for c in range(col_start, col_start + 5):
            if c >= 128:
                row += '.'
            else:
                row += '#' if anomaly_mask[r, c] else '.'
        pattern.append(row)
    print(f"  Char {ci} (cols {col_start}-{col_start+4}):")
    for row in pattern:
        print(f"    {row}")
    print()

# But wait - for char 0, the '7' needs its top bar which is in row 48
# So maybe char 0 of line 2 actually starts at col 15 but the first 
# character has content in row 48 while others don't

# Let me look at ALL of rows 48-54 for each char:
print("\n=== Full Line 2 (rows 48-54) at 6px pitch ===\n")
for ci in range(10):
    col_start = 15 + ci * 6
    print(f"  Char {ci} (cols {col_start}-{col_start+4}):")
    for r in range(48, 55):
        row = ''
        for c in range(col_start, col_start + 5):
            if c >= 128:
                row += '.'
            else:
                row += '#' if anomaly_mask[r, c] else '.'
        print(f"    {row}")
    print()
