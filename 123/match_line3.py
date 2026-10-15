import numpy as np
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

# Known font dictionary from Line 1 (GAIANSPACE) + Line 2 partially
# Each char is 5 cols wide, 6 rows tall (rows offset from body start)
# Let me build a proper font dictionary using ONLY the known characters

font = {}

# Line 1 chars (body: rows 37-42)
line1_known = "GAIANSPACE"
for ci, ch in enumerate(line1_known):
    cs = 12 + ci * 6
    pattern = []
    for r in range(37, 43):
        row = tuple(mask[r, cs:cs+5])
        pattern.append(row)
    font[ch] = tuple(pattern)

# { from cols 73-76 (4 wide) - special
# Skip for now

# Line 2 chars (body: rows 49-54)  
# We know: 7, T, H, -, C, L, A, S, S, -
line2_known = "7TH-CLASS-"
for ci, ch in enumerate(line2_known):
    cs = 15 + ci * 6
    pattern = []
    for r in range(49, 55):
        row = tuple(mask[r, cs:cs+5])
        pattern.append(row)
    if ch not in font:
        font[ch] = tuple(pattern)

# Print all known character patterns
print("="*60)
print("KNOWN FONT PATTERNS (5x6)")
print("="*60)
for ch in sorted(font.keys()):
    print(f"\n  '{ch}':")
    for row in font[ch]:
        print(f"    {''.join('█' if v else '·' for v in row)}")

# Now match Line 3 characters against known font
print("\n" + "="*60)
print("LINE 3 CHARACTER MATCHING")
print("="*60)

line3_chars = []
for ci in range(7):
    cs = 24 + ci * 6
    pattern = []
    for r in range(61, 67):
        row = tuple(mask[r, cs:cs+5])
        pattern.append(row)
    
    # Compare to all known chars
    results = []
    for known_ch, known_pat in font.items():
        matches = 0
        total = 0
        for pr, kr in zip(pattern, known_pat):
            for pv, kv in zip(pr, kr):
                total += 1
                if pv == kv:
                    matches += 1
        score = matches / total
        results.append((known_ch, score, matches, total))
    
    results.sort(key=lambda x: -x[1])
    
    best_ch = results[0][0]
    line3_chars.append(best_ch)
    
    print(f"\n  Char {ci} (cols {cs}-{cs+4}):")
    for row in pattern:
        print(f"    {''.join('█' if v else '·' for v in row)}")
    print(f"  Top 5 matches:")
    for ch, score, matches, total in results[:5]:
        print(f"    '{ch}': {score:.1%} ({matches}/{total})")

line3_str = ''.join(line3_chars)
print(f"\n\nLine 3 decoded: {line3_str}")
print(f"\nFull flag: GAIANSPACE{{7TH-CLASS-{line3_str}}}")

# Let's also check: what if the } isn't the last character in line 3?
# The } might be at a different column position
# Check the occupancy at cols 60-68
print("\n\nChecking for } location:")
for r in range(59, 69):
    line = ''
    for c in range(58, 70):
        line += '█' if mask[r, c] else '·'
    print(f"  {r}: {line} (cols 58-69)")

# Also, is the last char in line 3 actually }?
# Line 3 char 6 pattern:
print("\n\nLine 3 Char 6 pattern vs { pattern:")
print("  Char 6:")
for r in range(61, 67):
    row = tuple(mask[r, 60:65])
    print(f"    {''.join('█' if v else '·' for v in row)}")

print("  { from line 1 (cols 73-76):")
for r in range(37, 43):
    row = tuple(mask[r, 73:77])
    print(f"    {''.join('█' if v else '·' for v in row)}")

# } should be the mirror of {
# { = ·███/·███/███·/·███/·███/·███
# } = ███·/███·/·███/███·/███·/███·
print("\n  Expected } (mirror of {):")
print("    ███·")
print("    ███·")
print("    ·███")
print("    ███·")
print("    ███·")
print("    ███·")
