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

# The characters are rendered in BOLD - the letter shapes are FILLED blocks
# The gaps/holes in the pattern define the actual character
# Let me invert and look at each character

# 5x6 standard font definitions (inverted patterns = the dark pixels)
# Actually let me look at the patterns differently
# Each char is 6 cols wide (5 char cols + 1 gap)
# The first 5 cols contain the character, column 6 is always the gap

# For Line 1, we KNOW the text is "GAIANSPACE"
# Let me extract the 5x6 character patterns for each known letter

print("=== LINE 1: Known to be 'GAIANSPACE' ===")
print("Extracting character patterns (inverted = character shape):\n")

known = "GAIANSPACE"
char_patterns = {}

for ci, ch in enumerate(known):
    col_start = 12 + ci * 6
    # Extract 5 cols x 6 rows (excluding the gap column)
    pattern = []
    pattern_inv = []
    for r in range(37, 43):
        row = ''
        row_inv = ''
        for c in range(col_start, col_start + 5):
            row += '#' if anomaly_mask[r, c] else '.'
            row_inv += '.' if anomaly_mask[r, c] else '#'
        pattern.append(row)
        pattern_inv.append(row_inv)
    
    print(f"  '{ch}' (char {ci}, cols {col_start}-{col_start+4}):")
    print(f"    Normal:    Inverted:")
    for i in range(6):
        print(f"    {pattern[i]}      {pattern_inv[i]}")
    print()
    
    # Store the pattern (as tuple of rows for matching)
    char_patterns[ch] = tuple(pattern)

# Now extract and match Line 2 characters
print("\n=== LINE 2: Unknown - matching against known patterns ===\n")
line2_chars = []
for ci in range(10):
    col_start = 15 + ci * 6
    pattern = []
    for r in range(49, 55):  # Skip top row which is padding
        row = ''
        for c in range(col_start, col_start + 5):
            if c >= 128:
                row += '.'
            else:
                row += '#' if anomaly_mask[r, c] else '.'
        pattern.append(row)
    
    pattern_tuple = tuple(pattern)
    
    # Try to match against known patterns
    best_match_char = '?'
    best_match_score = 0
    for known_ch, known_pat in char_patterns.items():
        # Compare pixel-by-pixel
        matches = sum(1 for a, b in zip(''.join(pattern), ''.join(known_pat)) if a == b)
        total = len(''.join(pattern))
        score = matches / total
        if score > best_match_score:
            best_match_score = score
            best_match_char = known_ch
    
    line2_chars.append((ci, pattern, best_match_char, best_match_score))
    
    print(f"  Char {ci} (cols {col_start}-{col_start+4}): best match='{best_match_char}' ({best_match_score:.2f})")
    for row in pattern:
        print(f"    {row}")
    print()

print(f"Line 2 decoded: {''.join(c[2] for c in line2_chars)}")

# Now Line 3
print("\n=== LINE 3: Unknown ===\n")
line3_chars = []
for ci in range(7):
    col_start = 24 + ci * 6
    if col_start + 4 > 127:
        break
    pattern = []
    for r in range(61, 67):
        row = ''
        for c in range(col_start, min(col_start + 5, 128)):
            row += '#' if anomaly_mask[r, c] else '.'
        # Pad if needed
        while len(row) < 5:
            row += '.'
        pattern.append(row)
    
    pattern_tuple = tuple(pattern)
    
    best_match_char = '?'
    best_match_score = 0
    for known_ch, known_pat in char_patterns.items():
        matches = sum(1 for a, b in zip(''.join(pattern), ''.join(known_pat)) if a == b)
        total = len(''.join(pattern))
        score = matches / total
        if score > best_match_score:
            best_match_score = score
            best_match_char = known_ch
    
    line3_chars.append((ci, pattern, best_match_char, best_match_score))
    
    print(f"  Char {ci} (cols {col_start}-{col_start+4}): best match='{best_match_char}' ({best_match_score:.2f})")
    for row in pattern:
        print(f"    {row}")
    print()

print(f"Line 3 decoded: {''.join(c[2] for c in line3_chars)}")

# Combined flag
print(f"\n=== COMBINED FLAG ===")
l2 = ''.join(c[2] for c in line2_chars)
l3 = ''.join(c[2] for c in line3_chars)
print(f"GAIANSPACE{{{l2}{l3}}}")
