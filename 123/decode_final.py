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

# Build font dictionary from KNOWN characters in Line 1
# Line 1: GAIANSPACE at rows 37-42, starting col 12, 6px pitch
known_text = "GAIANSPACE"
known_font = {}

print("=== Building font from known 'GAIANSPACE' ===\n")
for ci, ch in enumerate(known_text):
    col_start = 12 + ci * 6
    rows = []
    for r in range(37, 43):
        row = tuple(anomaly_mask[r, col_start:col_start + 5])
        rows.append(row)
    pattern = tuple(rows)
    
    if ch not in known_font:
        known_font[ch] = pattern
    
    # Print
    print(f"  '{ch}': ", end="")
    for row in rows:
        print(''.join('#' if v else '.' for v in row), end=" / ")
    print()

# Also extract the '{' from cols 73-76 (4 wide, but let's use 5 cols)
# Actually '{' is at cols 73-76 which is 4 cols. Let me check with 5 cols
print(f"\n  '{{' from cols 73-77:")
rows = []
for r in range(37, 43):
    row = tuple(anomaly_mask[r, 73:78])
    rows.append(row)
    print(f"    {''.join('#' if v else '.' for v in row)}")
known_font['{'] = tuple(rows)

# For '-' we can get it from Line 2 (confirmed hyphen at char 3 and char 9)
print(f"\n  '-' from Line 2 char 3 (cols 33-37):")
rows = []
for r in range(49, 55):
    row = tuple(anomaly_mask[r, 33:38])
    rows.append(row)
    print(f"    {''.join('#' if v else '.' for v in row)}")
known_font['-'] = tuple(rows)

# For '}' from Line 3 char 6 (cols 60-64)
print(f"\n  '}}' from Line 3 char 6 (cols 60-64):")
rows = []
for r in range(61, 67):
    row = tuple(anomaly_mask[r, 60:65])
    rows.append(row)
    print(f"    {''.join('#' if v else '.' for v in row)}")
known_font['}'] = tuple(rows)

# Now we know: G, A, I, N, S, P, C, E, {, -, }
# The characters we KNOW from context: the word between hyphens is probably CLASS
# So we also have L from "CLASS"
# L would be at Line 2 char 5 (cols 45-49)
print(f"\n  Checking Line 2 chars 4-8 for 'CLASS':")
for ci, ch in enumerate("CLASS"):
    col_start = 39 + ci * 6
    print(f"    '{ch}' at cols {col_start}-{col_start+4}:")
    rows = []
    for r in range(49, 55):
        row = tuple(anomaly_mask[r, col_start:col_start + 5])
        rows.append(row)
        print(f"      {''.join('#' if v else '.' for v in row)}")
    if ch not in known_font:
        known_font[ch] = tuple(rows)

# Note: C and A and S are already in our font from GAIANSPACE
# The 'L' is new
print(f"\n  'L' extracted from Line 2:")
print(f"    Pattern: ", end="")
for row in known_font['L']:
    print(''.join('#' if v else '.' for v in row), end=" / ")
print()

# Now let's verify CLASS matches our patterns
print(f"\n=== Verifying CLASS pattern match ===")
for ci, ch in enumerate("CLASS"):
    col_start = 39 + ci * 6
    observed = []
    for r in range(49, 55):
        row = tuple(anomaly_mask[r, col_start:col_start + 5])
        observed.append(row)
    
    # Match against all known chars
    best_ch = '?'
    best_score = 0
    for known_ch, known_pat in known_font.items():
        if len(known_pat) != len(observed):
            continue
        matches = sum(1 for a, b in zip([v for row in observed for v in row], 
                                          [v for row in known_pat for v in row]) if a == b)
        total = len([v for row in observed for v in row])
        score = matches / total
        if score > best_score:
            best_score = score
            best_ch = known_ch
    
    print(f"  Pos {ci} (expected '{ch}'): best='{best_ch}' ({best_score:.2f})")

# Now decode the unknowns
print(f"\n=== DECODING UNKNOWNS ===\n")

# Line 2 chars 0-2 (before first '-')
print("Line 2 first 3 chars:")
line2_prefix = ""
for ci in range(3):
    col_start = 15 + ci * 6
    observed = []
    for r in range(49, 55):
        row = tuple(anomaly_mask[r, col_start:col_start + 5])
        observed.append(row)
    
    results = []
    for known_ch, known_pat in known_font.items():
        if len(known_pat) != len(observed):
            continue
        matches = sum(1 for a, b in zip([v for row in observed for v in row], 
                                          [v for row in known_pat for v in row]) if a == b)
        total = len([v for row in observed for v in row])
        score = matches / total
        results.append((known_ch, score))
    results.sort(key=lambda x: -x[1])
    
    best = results[0][0]
    line2_prefix += best
    print(f"  Char {ci}: ", end="")
    for row in observed:
        print(''.join('#' if v else '.' for v in row), end=" / ")
    print()
    print(f"    Top matches: {results[:5]}")

# Line 3 chars 0-5 (before '}')
print("\nLine 3 first 6 chars:")
line3_content = ""
for ci in range(6):
    col_start = 24 + ci * 6
    observed = []
    for r in range(61, 67):
        row = tuple(anomaly_mask[r, col_start:col_start + 5])
        observed.append(row)
    
    results = []
    for known_ch, known_pat in known_font.items():
        if len(known_pat) != len(observed):
            continue
        matches = sum(1 for a, b in zip([v for row in observed for v in row], 
                                          [v for row in known_pat for v in row]) if a == b)
        total = len([v for row in observed for v in row])
        score = matches / total
        results.append((known_ch, score))
    results.sort(key=lambda x: -x[1])
    
    best = results[0][0]
    line3_content += best
    print(f"  Char {ci}: ", end="")
    for row in observed:
        print(''.join('#' if v else '.' for v in row), end=" / ")
    print()
    print(f"    Top matches: {results[:5]}")

print(f"\n=== FINAL FLAG ===")
print(f"Line 2 prefix: {line2_prefix}")
print(f"Line 3 content: {line3_content}")
print(f"Flag: GAIANSPACE{{{line2_prefix}-CLASS-{line3_content}}}")
