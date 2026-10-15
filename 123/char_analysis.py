import numpy as np
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')
red = tile[0].astype(float)
swir = tile[4].astype(float)

pop_a = (red < 15)  # low red
pop_b = ~pop_a       # high red
text_a = (pop_a & (swir > 70)).astype(np.uint8)
text_b = (pop_b & (swir < 70)).astype(np.uint8)
mask = (text_a | text_b)

# Let's analyze each line character by character
# First, find the vertical columns where text exists

print("="*80)
print("LINE 1 - Full rows 36-43, cols 10-78")
print("="*80)
for r in range(36, 44):
    line = ''
    for c in range(10, 78):
        line += '█' if mask[r, c] else '·'
    print(f'{r}: {line}')

# Find character boundaries by looking for vertical gaps (columns with no text)
print("\nColumn occupancy (line 1, rows 37-42):")
col_occ = []
for c in range(10, 78):
    count = sum(mask[r, c] for r in range(37, 43))
    col_occ.append((c, count))
    
occupancy_str = ''
for c, count in col_occ:
    occupancy_str += str(count) if count > 0 else '·'
print(f"  {occupancy_str}")

# Find gaps (runs of 0s)
in_char = False
char_starts = []
for c, count in col_occ:
    if count > 0 and not in_char:
        char_starts.append(c)
        in_char = True
    elif count == 0 and in_char:
        in_char = False

print(f"\nCharacter column starts: {char_starts}")

# Now extract each character pattern between starts
# Using 6-pixel pitch as the character width (5px char + 1px gap)
print("\nExtracting characters (6px pitch from col starts):")

# Actually, let me just read the pattern more carefully
# Line 1 known: GAIANSPACE{
# The text body is rows 37-42 (6 rows high)
# Let me find exact character positions

# Approach: scan for connected regions in each line
for line_name, body_rows, scan_start, scan_end in [
    ("LINE 1", range(37, 43), 10, 78),
    ("LINE 2", range(49, 55), 12, 78),
    ("LINE 3", range(61, 67), 22, 68)
]:
    print(f"\n{'='*80}")
    print(f"{line_name} body (rows {body_rows[0]}-{body_rows[-1]})")
    print(f"{'='*80}")
    
    for r in body_rows:
        line = ''
        for c in range(scan_start, scan_end):
            line += '█' if mask[r, c] else '·'
        print(f'  {r}: {line}')
    
    # Column occupancy
    print(f"\n  Column occupancy ({scan_start}-{scan_end}):")
    occ = []
    for c in range(scan_start, scan_end):
        count = sum(mask[r, c] for r in body_rows)
        occ.append((c, count))
    
    # Print occupancy
    occ_str = ''
    for c, count in occ:
        occ_str += str(count) if count > 0 else '·'
    print(f"  {occ_str}")
    
    # Find gaps (consecutive 0-columns)
    print(f"\n  Segments (runs of occupied columns):")
    segments = []
    in_seg = False
    seg_start = 0
    for c, count in occ:
        if count > 0 and not in_seg:
            seg_start = c
            in_seg = True
        elif count == 0 and in_seg:
            segments.append((seg_start, c - 1, c - seg_start))
            in_seg = False
    if in_seg:
        segments.append((seg_start, occ[-1][0], occ[-1][0] - seg_start + 1))
    
    for start, end, width in segments:
        print(f"    Cols {start}-{end} (width={width})")
        for r in body_rows:
            line = ''
            for c in range(start, end + 1):
                line += '█' if mask[r, c] else '·'
            print(f"      {r}: {line}")
        print()

# Now zoom into specific characters
# Line 2 body: rows 49-54
# Line 3 body: rows 61-66
print("\n" + "="*80)
print("DETAILED CHARACTER ANALYSIS")
print("="*80)

# From the output, line 2 appears to be: 7TH-CLASS-
# and line 3 appears to contain the remaining flag text + }

# Let me print each 6-pixel-wide column block for line 3
print("\nLine 3 - character slices (6px wide, 1px gap assumed):")
# From the ASCII art, line 3 text starts around col 24
for ci in range(8):
    col_start = 24 + ci * 6
    col_end = col_start + 5
    print(f"\n  Char {ci} (cols {col_start}-{col_end}):")
    for r in range(61, 67):
        line = ''
        for c in range(col_start, col_end + 1):
            line += '█' if mask[r, c] else '·'
        print(f"    {r}: {line}")

# Also print line 2 character slices
print("\nLine 2 - character slices:")
for ci in range(11):
    col_start = 15 + ci * 6
    col_end = col_start + 5
    print(f"\n  Char {ci} (cols {col_start}-{col_end}):")
    for r in range(49, 55):
        line = ''
        for c in range(col_start, col_end + 1):
            line += '█' if mask[r, c] else '·'
        print(f"    {r}: {line}")
