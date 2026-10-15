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

# Define a comprehensive bold 5x6 pixel font
# Pattern: each letter shown as 6 rows of 5 characters (bold/filled style)
# In this font, the letter is CARVED OUT of a filled block
# So 'G' has gap at top-left and right-middle

# Standard 5x7 font inverted patterns (what the gaps look like):
FONT_INV = {
    'A': ['..#..', '.#.#.', '#...#', '#####', '#...#', '#...#'],  # Triangle with crossbar
    'B': ['####.', '#...#', '####.', '#...#', '#...#', '####.'],
    'C': ['.###.', '#...#', '#....', '#....', '#...#', '.###.'],
    'D': ['####.', '#...#', '#...#', '#...#', '#...#', '####.'],
    'E': ['#####', '#....', '####.', '#....', '#....', '#####'],
    'F': ['#####', '#....', '####.', '#....', '#....', '#....'],
    'G': ['.###.', '#...#', '#....', '#.###', '#...#', '.###.'],  # or ['.####', '#....', '#....', '#.##.', '#..#.', '.###.']
    'H': ['#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'I': ['#####', '..#..', '..#..', '..#..', '..#..', '#####'],
    'J': ['..###', '...#.', '...#.', '...#.', '#..#.', '.##..'],
    'K': ['#..#.', '#.#..', '##...', '#.#..', '#..#.', '#...#'],
    'L': ['#....', '#....', '#....', '#....', '#....', '#####'],
    'M': ['#...#', '##.##', '#.#.#', '#...#', '#...#', '#...#'],
    'N': ['#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#'],
    'O': ['.###.', '#...#', '#...#', '#...#', '#...#', '.###.'],
    'P': ['####.', '#...#', '#...#', '####.', '#....', '#....'],
    'Q': ['.###.', '#...#', '#...#', '#.#.#', '#..#.', '.##.#'],
    'R': ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.'],
    'S': ['.####', '#....', '.###.', '....#', '....#', '####.'],
    'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..'],
    'U': ['#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    'V': ['#...#', '#...#', '#...#', '.#.#.', '.#.#.', '..#..'],
    'W': ['#...#', '#...#', '#.#.#', '#.#.#', '.#.#.', '.#.#.'],
    'X': ['#...#', '.#.#.', '..#..', '..#..', '.#.#.', '#...#'],
    'Y': ['#...#', '.#.#.', '..#..', '..#..', '..#..', '..#..'],
    'Z': ['#####', '...#.', '..#..', '.#...', '#....', '#####'],
    '0': ['.###.', '#..##', '#.#.#', '##..#', '#...#', '.###.'],
    '1': ['..#..', '.##..', '..#..', '..#..', '..#..', '.###.'],
    '2': ['.###.', '#...#', '...#.', '..#..', '.#...', '#####'],
    '3': ['#####', '...#.', '..#..', '...#.', '#...#', '.###.'],
    '4': ['...#.', '..##.', '.#.#.', '#..#.', '#####', '...#.'],
    '5': ['#####', '#....', '####.', '....#', '#...#', '.###.'],
    '6': ['.###.', '#....', '####.', '#...#', '#...#', '.###.'],
    '7': ['#####', '....#', '...#.', '..#..', '.#...', '.#...'],
    '8': ['.###.', '#...#', '.###.', '#...#', '#...#', '.###.'],
    '9': ['.###.', '#...#', '.####', '....#', '...#.', '.##..'],
    '-': ['.....', '.....', '#####', '.....', '.....', '.....'],
    '{': ['..##.', '.#...', '#....', '.#...', '.#...', '..##.'],
    '}': ['.##..', '...#.', '....#', '...#.', '...#.', '.##..'],
    '_': ['.....', '.....', '.....', '.....', '.....', '#####'],
}

# Now BOLD the font: invert each char (# -> ., . -> #)
FONT_BOLD = {}
for ch, rows in FONT_INV.items():
    bold_rows = []
    for row in rows:
        bold_rows.append(''.join('#' if c == '.' else '.' for c in row))
    FONT_BOLD[ch] = bold_rows

# Display the bold font for reference chars
print("Bold font reference:")
for ch in "GAIANSPACE{7-}":
    if ch in FONT_BOLD:
        print(f"  '{ch}':")
        for row in FONT_BOLD[ch]:
            print(f"    {row}")
        print()

# Now match each character position against the bold font
def match_char(observed_rows, font_bold):
    """Match observed character pattern against all font characters"""
    scores = {}
    for ch, ref_rows in font_bold.items():
        if len(ref_rows) != len(observed_rows):
            continue
        total = 0
        matches = 0
        for obs_row, ref_row in zip(observed_rows, ref_rows):
            for o, r in zip(obs_row, ref_row):
                total += 1
                if o == r:
                    matches += 1
        scores[ch] = matches / total if total > 0 else 0
    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return ranked

# Extract and match all characters
print("\n=== MATCHING ALL CHARACTERS ===\n")

# Line 1: GAIANSPACE (for validation)
print("--- Line 1 (validation, should be GAIANSPACE) ---")
for ci in range(10):
    col_start = 12 + ci * 6
    observed = []
    for r in range(37, 43):
        row = ''.join('#' if anomaly_mask[r, c] else '.' for c in range(col_start, col_start + 5))
        observed.append(row)
    ranked = match_char(observed, FONT_BOLD)
    print(f"  Char {ci}: best='{ranked[0][0]}' ({ranked[0][1]:.2f}), "
          f"2nd='{ranked[1][0]}' ({ranked[1][1]:.2f}), "
          f"3rd='{ranked[2][0]}' ({ranked[2][1]:.2f})")

# Line 2  
print("\n--- Line 2 ---")
line2_result = ""
for ci in range(10):
    col_start = 15 + ci * 6
    observed = []
    for r in range(49, 55):  # 6 rows
        row = ''.join('#' if anomaly_mask[r, c] else '.' for c in range(col_start, col_start + 5))
        observed.append(row)
    ranked = match_char(observed, FONT_BOLD)
    best = ranked[0][0]
    line2_result += best
    print(f"  Char {ci}: best='{ranked[0][0]}' ({ranked[0][1]:.2f}), "
          f"2nd='{ranked[1][0]}' ({ranked[1][1]:.2f}), "
          f"3rd='{ranked[2][0]}' ({ranked[2][1]:.2f})")

# Line 3
print("\n--- Line 3 ---")
line3_result = ""
for ci in range(7):
    col_start = 24 + ci * 6
    if col_start + 4 > 127:
        break
    observed = []
    for r in range(61, 67):
        row = ''.join('#' if anomaly_mask[r, c] else '.' for c in range(col_start, min(col_start + 5, 128)))
        while len(row) < 5:
            row += '.'
        observed.append(row)
    ranked = match_char(observed, FONT_BOLD)
    best = ranked[0][0]
    line3_result += best
    print(f"  Char {ci}: best='{ranked[0][0]}' ({ranked[0][1]:.2f}), "
          f"2nd='{ranked[1][0]}' ({ranked[1][1]:.2f}), "
          f"3rd='{ranked[2][0]}' ({ranked[2][1]:.2f})")

print(f"\n=== DECODED FLAG ===")
print(f"Line 2: {line2_result}")
print(f"Line 3: {line3_result}")
print(f"Flag: GAIANSPACE{{{line2_result}{line3_result}}}")
