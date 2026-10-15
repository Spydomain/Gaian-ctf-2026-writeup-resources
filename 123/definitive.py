import numpy as np
from PIL import Image, ImageDraw, ImageFont
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')
red = tile[0].astype(float)
swir = tile[4].astype(float)

# Compute text mask using population inversion method  
pop_a = (red < 15)
pop_b = ~pop_a
text_a = (pop_a & (swir > 70)).astype(np.uint8)
text_b = (pop_b & (swir < 70)).astype(np.uint8)
mask = (text_a | text_b)

# Clean gap columns (known from 6px pitch analysis)
clean = mask.copy()

# Line 1 gap cols at positions: 12+5=17, 18+5=23, 24+5=29, etc.
for ci in range(10):
    gc = 12 + ci * 6 + 5  # gap column
    for r in range(36, 44):
        clean[r, gc] = 0

# Line 2 gap cols
for ci in range(10):
    gc = 15 + ci * 6 + 5
    for r in range(47, 56):
        clean[r, gc] = 0

# Line 3 gap cols
for ci in range(7):
    gc = 24 + ci * 6 + 5
    for r in range(59, 68):
        clean[r, gc] = 0

# Also clean the "border" rows (first and last rows of each text line)
# These often contain noise. Let's keep them but check if they're part of chars

# Clean top/bottom padding rows
for c in range(128):
    clean[36, c] = 0  # row above line 1 body
    clean[43, c] = 0  # row below line 1 body (except for { which goes to 43?)
    # Actually be more careful - { extends to row 43
    
    clean[47, c] = 0  # row above line 2 body
    clean[48, c] = 0  # row between padding
    clean[55, c] = 0  # row below line 2 body
    
    clean[59, c] = 0  # row above line 3
    clean[60, c] = 0  # row between padding (except for tail above })
    clean[67, c] = 0  # row below line 3
    
# But keep { and } tails
# { has body rows 37-42 at cols 73-76
# } should be at end of line 3

# Re-render line 3 with clean mask
print("CLEANEST Line 3 (rows 61-66, cols 24-64):")
for r in range(61, 67):
    line = ''
    for c in range(24, 65):
        line += '█' if clean[r, c] else '·'
    print(f'  {r}: {line}')

# Extract each character cleanly
print("\nLine 3 character patterns (5px wide, 6 rows):")
chars_text = []
for ci in range(7):
    cs = 24 + ci * 6
    pat = []
    print(f"\n  Char {ci} (cols {cs}-{cs+4}):")
    for r in range(61, 67):
        row = ''
        for c in range(cs, cs + 5):
            row += '█' if clean[r, c] else '·'
        pat.append(row)
        print(f"    {row}")
    chars_text.append(pat)

# Now let me try to read these as actual bitmap font characters
# The font appears to be a 5-wide, 6-tall bitmap with thick strokes

# Let me build a comprehensive font from KNOWN characters (Line 1 + Line 2)
# and see what's left unknown

known_patterns = {}
# Line 1: GAIANSPACE at cols 12,18,24,30,36,42,48,54,60,66
for ci, ch in enumerate("GAIANSPACE"):
    cs = 12 + ci * 6
    pat = []
    for r in range(37, 43):
        row = ''
        for c in range(cs, cs + 5):
            row += '█' if clean[r, c] else '·'
        pat.append(row)
    known_patterns[ch] = pat

# Line 2: 7TH-CLASS- at cols 15,21,27,33,39,45,51,57,63,69
for ci, ch in enumerate("7TH-CLASS-"):
    cs = 15 + ci * 6
    pat = []
    for r in range(49, 55):
        row = ''
        for c in range(cs, cs + 5):
            row += '█' if clean[r, c] else '·'
        pat.append(row)
    if ch not in known_patterns:
        known_patterns[ch] = pat

print("\n\nKNOWN CHARACTER PATTERNS:")
for ch in sorted(known_patterns.keys()):
    print(f"\n  '{ch}':")
    for row in known_patterns[ch]:
        print(f"    {row}")

# Compare line 3 chars to known patterns
print("\n\nLINE 3 CHARACTER IDENTIFICATION:")
for ci in range(7):
    pat = chars_text[ci]
    print(f"\n  Char {ci}:")
    for row in pat:
        print(f"    {row}")
    
    # Find closest match by hamming distance
    scores = []
    for ch, kpat in known_patterns.items():
        dist = 0
        for pr, kr in zip(pat, kpat):
            for pc, kc in zip(pr, kr):
                if pc != kc:
                    dist += 1
        scores.append((ch, dist))
    scores.sort(key=lambda x: x[1])
    
    print(f"  Matches (distance):")
    for ch, dist in scores[:5]:
        pct = (30 - dist) / 30 * 100
        print(f"    '{ch}': distance={dist} ({pct:.0f}% match)")

# Now render the final CLEAN image at high resolution
# Create a 3-panel image showing all 3 lines

scale = 30  # Very high resolution

# Line 3 with character boundaries
y0, y1 = 61, 67
x0, x1 = 24, 65
region = clean[y0:y1, x0:x1]
h, w = region.shape
big = np.repeat(np.repeat(region * 255, scale, axis=0), scale, axis=1)
img = Image.fromarray(big, mode='L').convert('RGB')
draw = ImageDraw.Draw(img)

# Draw character boundaries as thin red lines
for ci in range(8):
    x = ci * 6 * scale
    if x < img.width:
        draw.line([(x, 0), (x, img.height - 1)], fill=(255, 0, 0), width=2)

# Draw gap columns in blue
for ci in range(7):
    x_gap_start = (ci * 6 + 5) * scale
    x_gap_end = (ci * 6 + 6) * scale - 1
    if x_gap_start < img.width:
        draw.rectangle([(x_gap_start, 0), (min(x_gap_end, img.width-1), img.height-1)], 
                       outline=(0, 0, 255), width=1)

img.save('definitive_line3.png')
print("\nSaved definitive_line3.png")

# Full 3-line image with labels
# Calculate dimensions
line_configs = [
    ("GAIANSPACE{", 37, 43, 12, 77, [12 + i*6 for i in range(10)] + [73]),
    ("7TH-CLASS-",   49, 55, 15, 75, [15 + i*6 for i in range(10)]),
    ("???????}",     61, 67, 24, 65, [24 + i*6 for i in range(7)]),
]

max_width = max(x1 - x0 for _, _, _, x0, x1, _ in line_configs)
total_height = sum(y1 - y0 for _, y0, y1, _, _, _ in line_configs) + 2 * 2  # 2px gap between lines

full_h = total_height * scale + 3 * 40  # label space
full_w = max_width * scale + 20

full_img = Image.new('RGB', (full_w, full_h), (0, 0, 0))
full_draw = ImageDraw.Draw(full_img)

y_offset = 10
for label, y0, y1, x0, x1, char_starts in line_configs:
    # Label
    full_draw.text((10, y_offset), label, fill=(255, 255, 0))
    y_offset += 20
    
    # Image
    region = clean[y0:y1, x0:x1]
    h, w = region.shape
    big = np.repeat(np.repeat(region * 255, scale, axis=0), scale, axis=1)
    line_img = Image.fromarray(big, mode='L').convert('RGB')
    
    full_img.paste(line_img, (10, y_offset))
    
    # Draw character boundaries
    for cs in char_starts:
        x = (cs - x0) * scale + 10
        full_draw.line([(x, y_offset), (x, y_offset + h * scale - 1)], fill=(255, 0, 0), width=1)
    
    y_offset += h * scale + 20

full_img.save('definitive_all.png')
print("Saved definitive_all.png")
