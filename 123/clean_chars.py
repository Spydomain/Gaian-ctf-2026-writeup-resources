import numpy as np
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')
red = tile[0].astype(float)
swir = tile[4].astype(float)

pop_a = (red < 15)
pop_b = ~pop_a
text_a = (pop_a & (swir > 70)).astype(np.uint8)
text_b = (pop_b & (swir < 70)).astype(np.uint8)
mask = (text_a | text_b)

# Key insight: characters are 5px wide with 1px gaps (6px pitch)
# The gap columns might have 1-2 stray pixels (noise)
# We can identify gap columns as those with occupancy <= 2

# Let's use the known starting positions and 6px pitch
# Line 1: starts at col 12, GAIANSPACE (10 chars), then gap, then { at col 73
# 12 + 10*6 = 72, and { starts at 73 - perfect! Each char is 5px with 1px gap

# So characters are at: col, col+1, col+2, col+3, col+4  (5 wide)
# Gap is at: col+5
# Next char starts at: col+6

# Line 1: col_start=12, chars at 12,18,24,30,36,42,48,54,60,66 then { at 73
# Line 2: Let's figure out start
# Line 2 segment starts at col 15 (width 60)
# If 10 chars: 15,21,27,33,39,45,51,57,63,69 → 69+5=74, end of segment should be 74
# Line 2 ends at 74 → perfect for 10 chars!

# Line 3: segment starts at col 24, width 41
# 24 to 64. If we try 7 chars of 6px: 24,30,36,42,48,54,60 → 60+4=64. 
# That's 7 chars of 5px = 35px + 6 gaps of 1px = 41px total. 
# But wait, we also need the } character at the end

# Actually let's count: line 3 = last part of flag + }
# From the challenge, flag is GAIANSPACE{...}
# Line 1: GAIANSPACE{ (11 chars)
# Line 2: 10 chars
# Line 3: remaining chars + }
# Line 3 cols 24-64 = 41 columns. If 7 chars: 7*5 + 6*1 = 41. Yes!
# So line 3 has 7 characters

# Let me now cleanly extract each character using the KNOWN 6px pitch
# and REMOVE the gap noise by zeroing the gap column

# Create clean mask by zeroing gap columns
clean = mask.copy()

# Line 1: chars at cols 12,18,24,30,36,42,48,54,60,66 (5px wide each)
# Gap columns: 17,23,29,35,41,47,53,59,65,71
line1_chars_start = [12, 18, 24, 30, 36, 42, 48, 54, 60, 66]
line1_gap_cols = [17, 23, 29, 35, 41, 47, 53, 59, 65, 71, 72]

# { at col 73, 4px wide (73,74,75,76)
line1_chars_start.append(73)  # {

# Line 2: chars at cols 15,21,27,33,39,45,51,57,63,69
line2_chars_start = [15, 21, 27, 33, 39, 45, 51, 57, 63, 69]
line2_gap_cols = [20, 26, 32, 38, 44, 50, 56, 62, 68, 74]

# Line 3: chars at cols 24,30,36,42,48,54,60
line3_chars_start = [24, 30, 36, 42, 48, 54, 60]
line3_gap_cols = [29, 35, 41, 47, 53, 59, 65]

# Zero out the gap columns to clean up noise
for gc in line1_gap_cols:
    for r in range(36, 44):
        clean[r, gc] = 0

for gc in line2_gap_cols:
    for r in range(47, 56):
        clean[r, gc] = 0

for gc in line3_gap_cols:
    for r in range(59, 68):
        clean[r, gc] = 0

# Now extract and print clean characters
print("="*80)
print("CLEAN CHARACTER EXTRACTION")
print("="*80)

known_line1 = "GAIANSPACE{"
known_line2_guess = "7TH-CLASS-"

for line_name, chars_start, body_rows, known in [
    ("LINE 1", line1_chars_start, range(37, 43), known_line1),
    ("LINE 2", line2_chars_start, range(49, 55), known_line2_guess),
    ("LINE 3", line3_chars_start, range(61, 67), "???????")
]:
    print(f"\n{line_name}:")
    for ci, cs in enumerate(chars_start):
        char_width = 5 if cs != 73 else 4  # { is 4 wide
        known_ch = known[ci] if ci < len(known) else '?'
        print(f"\n  Char {ci} = '{known_ch}' (cols {cs}-{cs+char_width-1}):")
        for r in body_rows:
            line = '    '
            for c in range(cs, cs + char_width):
                line += '█' if clean[r, c] else '·'
            print(line)

# Now save the clean image
scale = 20

# Full clean image
region = clean[35:70, 10:80]
big = np.repeat(np.repeat(region * 255, scale, axis=0), scale, axis=1)
Image.fromarray(big, mode='L').save('cleanest_full.png')
print("\nSaved cleanest_full.png")

# Individual lines with grid overlay showing character boundaries
from PIL import ImageDraw

for line_name, chars_start, y0, y1, x0, x1 in [
    ("line1", line1_chars_start, 36, 44, 10, 78),
    ("line2", line2_chars_start, 47, 56, 12, 78),
    ("line3", line3_chars_start, 59, 68, 22, 68)
]:
    region = clean[y0:y1, x0:x1]
    big = np.repeat(np.repeat(region * 255, scale, axis=0), scale, axis=1)
    img = Image.fromarray(big, mode='L').convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # Draw character boundary lines
    for cs in chars_start:
        if cs >= x0 and cs <= x1:
            # Start of character
            x_pixel = (cs - x0) * scale
            draw.line([(x_pixel, 0), (x_pixel, img.height - 1)], fill=(255, 0, 0), width=1)
            # End of character (5px later)
            char_w = 5 if cs != 73 else 4
            x_end = (cs - x0 + char_w) * scale
            if x_end < img.width:
                draw.line([(x_end, 0), (x_end, img.height - 1)], fill=(0, 0, 255), width=1)
    
    img.save(f'cleanest_{line_name}_grid.png')
    print(f"Saved cleanest_{line_name}_grid.png")

# Also save without grid
for line_name, y0, y1, x0, x1 in [
    ("line1", 36, 44, 10, 78),
    ("line2", 47, 56, 12, 78),
    ("line3", 59, 68, 22, 68)
]:
    region = clean[y0:y1, x0:x1]
    big = np.repeat(np.repeat(region * 255, scale, axis=0), scale, axis=1)
    Image.fromarray(big, mode='L').save(f'cleanest_{line_name}.png')
    print(f"Saved cleanest_{line_name}.png")
