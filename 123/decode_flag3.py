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

# The font is noisy. Instead of trying to match exact patterns, let me look at the
# INVERTED (hole/gap) patterns which define the character shapes.
# The characters that are carved into the filled block.

# Known inverted patterns (from GAIANSPACE):
# G: #..../...../.....## /...../...../##....   -> has right gaps in middle = 'G'
# A: ...../#..../...../...../...../....         -> gap at left in rows 1-2 = 'A'  
# I: ...../....#/....#/....#/....#/.....        -> gaps on both sides = 'I'
# C: #..../...../...##/...##/...../..           -> gap at left-top, right-middle = 'C'
# E: ...../...##/...../...##/...../..           -> gaps at right, rows 1,3 = 'E'
# S: ...../...#./...../##.../..#../..           -> S-curve gaps = 'S'
# P: ...../...../...../...../...##/...          -> gaps at right-bottom = 'P'
# N: ...../...../...../...../...../...#         -> gap only at bottom-right = 'N'

# Now let me look at the UNKNOWN characters' inverted patterns:

# Line 2 Char 0 (7 rows, rows 48-54):
#   Normal:    #####/#####/...##/..###/..###/.###./.###.
#   Inverted:  ...../...../##.../##.../##.../....#/....#
#   This has: full top, then diagonal gap going from left-top to right-bottom
#   This is a '7' (top bar, then descending diagonal)

# Line 2 Char 1 (6 rows, rows 49-54):
#   Normal:    #####/#####/.###./.###./.###./#####
#   Same as 'I' pattern! -> 'I' (but could be 'T'?)
#   'T' in this font would be: ##### / .###. / .###. / .###. / .###. / .###.
#   But our char has BOTH top and bottom bars, so it's 'I', not 'T'
#   Wait - 'T' would be: full top, then narrow without bottom bar
#   'H' would be: narrow, narrow, full, narrow, narrow
#   Ours: full/full/narrow/narrow/narrow/full = top heavy with bottom bar = 'I'

# But looking at the 7-row version:
# Row 48 (char 1): ..... (empty)
# Rows 49-54: #####/#####/.###./.###./.###./#####
# That's: empty, full, full, narrow, narrow, narrow, full
# The leading empty row is just padding. The char is 'I' or 'T'
# In context: 7I?-CLASS- ... the '7' followed by 'I' doesn't make obvious sense
# But '7th-CLASS-' would! Let me check if char 1 could be 't' (lowercase)

# Actually wait - in context of the CTF challenge about remote sensing classification:
# "ISODATA with 7 classes"
# The flag could be: GAIANSPACE{7th-CLASS-??????}
# "7th-CLASS" means the 7th classification class

# Let me check: is char 2 of line 2 'h'?
# Char 2 (rows 49-54): ##### / ##### / ##### / ##### / ##### / #####
# That's ALL FILLED - no gaps at all. This means 'N' (which also has minimal gaps)
# But in lowercase 'h': .####/###../###../####./####./####.  or similar
# All-filled could be 'h' in a bold font where the small hole of 'h' is lost to noise

# Or... perhaps the character grid alignment is slightly off

# Let me try a DIFFERENT approach: render candidate strings and compare
from PIL import Image, ImageFont, ImageDraw
import os

# Build the target patterns for each line  
# Line 1 target (rows 37-42, cols 12-76): GAIANSPACE{
# Line 2 target (rows 48-54, cols 15-74): ???-CLASS-
# Line 3 target (rows 61-66, cols 24-64): ?????}

# Try rendering candidate flags and computing similarity
def render_text(text, font):
    """Render text and return binary array"""
    img = Image.new('L', (200, 20), 0)
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), text, fill=255, font=font)
    arr = np.array(img)
    # Find bounds
    rows_with = np.any(arr > 0, axis=1)
    cols_with = np.any(arr > 0, axis=0)
    if not np.any(rows_with):
        return None
    r0, r1 = np.where(rows_with)[0][0], np.where(rows_with)[0][-1]
    c0, c1 = np.where(cols_with)[0][0], np.where(cols_with)[0][-1]
    return (arr[r0:r1+1, c0:c1+1] > 128).astype(np.uint8)

# Let me try DejaVuSansMono-Bold at various sizes
font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
if os.path.exists(font_path):
    for sz in range(5, 12):
        font = ImageFont.truetype(font_path, sz)
        rendered = render_text("GAIANSPACE", font)
        if rendered is not None:
            print(f"DejaVuSansMono-Bold sz={sz}: {rendered.shape}")

# Try the PIL default font
font = ImageFont.load_default()
rendered = render_text("GAIANSPACE{", font)
if rendered is not None:
    print(f"Default: {rendered.shape}")

# Our target is 6 rows high. Let me just manually look at the visual image
# and try to read the text

# Actually, let me try a completely different approach:
# The text might be rendered using numpy/matplotlib rather than a bitmap font
# Let me look at what common CTF tools produce

# Looking at the images again more carefully with the context:
# Line 1: GAIANSPACE{  (confirmed)
# Line 2: 7th-CLASS-   or  THE-CLASS-
# Line 3: ??????}

# For Line 2 char 0: The descending pattern from right to left is diagnostic.
# Normal patterns (rows 48-54):
# #####  <- full
# #####  <- full (top bar of '7')  
# ...##  <- only right side
# ..###  <- descending to the right
# ..###  
# .###.  <- more to the left
# .###.  
# This is clearly '7'!

# For Line 2 char 1 (rows 49-54):
# #####  <- full
# #####  <- full 
# .###.  <- narrow with gaps both sides
# .###.  
# .###.  
# #####  <- full bottom
# Looking at just these 6 rows - both top and bottom are full bars
# This matches 'I' NOT 'T' (T has no bottom bar)

# But semantically: 7I?-CLASS- doesn't make sense
# Maybe: 7TH-CLASS- and the 'T' has a slightly noisy bottom
# Let me check if there are pixels at the bottom corners

# Or maybe: THE-CLASS- with T-H-E
# Char 0 for 'T' would be: full top, narrow rest
# Our char 0: full/full/gaps_left/more_gaps/more_gaps/...
# That's diagonal, not centered narrow - so NOT T

# Let me try: maybe char 1 is 'T' and char 2 is 'H'
# 't' lowercase would start narrow and get wider? No.

# I'm going with '7' for char 0.
# For char 1, even though it looks like 'I', in context '7th' makes more sense
# 'T' in this bold font: ##### / .###. / .###. / .###. / .###. / .###.
# Our char: ##### / ##### / .###. / .###. / .###. / #####
# The difference is rows 1 and 5: our char has full rows there.
# But this could be noise - the classification isn't perfect

# For char 2: all filled. Could be 'h' with noise, or 'H'
# 'H' normal pattern: ##.## / ##.## / ##### / ##.## / ##.## / ##.##
# In bold: .##.# / .##.# / ##### / .##.# / .##.# / .##.#
# All filled could happen if the single-pixel gaps of H are lost to noise

# OK, so my best guess: Line 2 = "7TH-CLASS-" with noisy rendering

# For Line 3, let me look more carefully:
print("\n\n=== Line 3 detailed analysis ===")
print("Line 3 chars (rows 61-66):\n")

# Let me look at the inverted patterns for Line 3
for ci in range(7):
    col_start = 24 + ci * 6
    if col_start + 4 > 127:
        break
    print(f"  Char {ci} (cols {col_start}-{col_start+4}):")
    print(f"    Normal:    Inverted:")
    for r in range(61, 67):
        normal = ''.join('#' if anomaly_mask[r, c] else '.' for c in range(col_start, col_start + 5))
        inverted = ''.join('.' if anomaly_mask[r, c] else '#' for c in range(col_start, col_start + 5))
        print(f"    {normal}      {inverted}")
    print()

# Char 0: ###.#/.####/..###/..###/.####/###.#
# Inverted: ...#./#..../#.##./#.##./#....//...#.
# Top and bottom have gap at position 3, middle has gaps at 0 and 2,3
# This looks like 'X': diagonal cross pattern

# Char 1: #####/#####/#####/#####/#####/#####
# All filled - could be 'H' or 'N' or noise

# Char 2: #####/#####/.###./.###./.###./#####.
# Same as 'I' pattern (or 'T' without bottom gap?)
# Actually: .....top bar, narrow middle, bottom... wait
# Full/Full/narrow/narrow/narrow/Full-ish
# This is 'I' pattern

# Char 3: ###.#/.####/..###/..###/.####/###.#  
# Same as Char 0 = 'X'

# Wait, chars 0, 3, 5 of line 3 all have the SAME pattern!
# That's: X?IX?X?}

# Char 4: #####/#####/#####/#####/.####/.####
# Inverted: ...../...../...../....#/#..../#....
# Full except bottom-left and bottom-right gaps
# This could be 'Y': full top, then narrow bottom, or 'V' inverted

# Char 5: Same as chars 0, 3 = 'X'

# Char 6: ####./.###./..###/.###./.###./####.
# Inverted: ....#/#...#/##.../#...#/#...#/....#
# This has left gaps in rows 0,5 and right gaps in rows 1-4 alternating
# This looks like '}' !

# So Line 3 might be: XNIXYX}  or XHIXHX} or...

# But what makes sense semantically?
# GAIANSPACE{7TH-CLASS-XHIXHX}? That doesn't work.

# Let me reconsider. Maybe the word between the hyphens is different.
# Or maybe it's GAIANSPACE{THE-CLASS-??????}

# Actually, let me reconsider the challenge context:
# "count what actually grows here"
# "ISODATA with 7 classes"
# It's about land classification. The 7th class is the anomalous one.

# Maybe the flag is about what the 7th class IS:
# GAIANSPACE{7th-CLASS-MIXEDX}? 
# GAIANSPACE{7th-CLASS-MISFIT}?

# Wait - let me look at char 6 of line 3 again
# ####./.###./..###/.###./.###./####.
# This is definitely '}' (curly brace closing)

# So the flag content is: Line2 + Line3_chars_0_to_5 = 10 + 6 = 16 chars
# ???-CLASS-?????? 

# Hmm, let me check if the alignment might be off. What if the characters
# aren't perfectly on a 6px grid?

# Let me try different starting columns for each line
print("\n\n=== Testing alignment shifts ===\n")
for offset in [-1, 0, 1]:
    print(f"\nLine 3 with offset={offset}:")
    for ci in range(7):
        col_start = 24 + offset + ci * 6
        if col_start + 4 > 127 or col_start < 0:
            continue
        row_str = ""
        for r in range(61, 67):
            row = ''.join('#' if anomaly_mask[r, c] else '.' for c in range(col_start, col_start + 5))
            row_str += row + "/"
        print(f"  Char {ci}: {row_str}")
