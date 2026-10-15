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

# Print column-by-column occupancy for each line
# This will show us where the character gaps are

for line_name, body_rows, scan_start, scan_end in [
    ("LINE 1", range(37, 43), 10, 80),
    ("LINE 2", range(49, 55), 10, 80),
    ("LINE 3", range(61, 67), 20, 70)
]:
    print(f"\n{'='*80}")
    print(f"{line_name}")
    print(f"{'='*80}")
    
    # Print the text
    for r in body_rows:
        line = f'{r}: '
        for c in range(scan_start, scan_end):
            line += '█' if mask[r, c] else '·'
        print(line)
    
    # Print column numbers (tens)
    tens = '    '
    for c in range(scan_start, scan_end):
        tens += str(c // 10 % 10) if c % 10 == 0 else ' '
    print(tens)
    
    # Print column numbers (ones)
    ones = '    '
    for c in range(scan_start, scan_end):
        ones += str(c % 10)
    print(ones)
    
    # Print occupancy (count of text pixels in column)
    occ = '    '
    for c in range(scan_start, scan_end):
        count = sum(mask[r, c] for r in body_rows)
        occ += str(count) if count > 0 else '·'
    print(occ)
    
    # Find gap columns (columns with 0 text pixels)
    gaps = []
    for c in range(scan_start, scan_end):
        count = sum(mask[r, c] for r in body_rows)
        if count == 0:
            gaps.append(c)
    
    # Find gap runs
    gap_runs = []
    if gaps:
        run_start = gaps[0]
        for i in range(1, len(gaps)):
            if gaps[i] != gaps[i-1] + 1:
                gap_runs.append((run_start, gaps[i-1]))
                run_start = gaps[i]
        gap_runs.append((run_start, gaps[-1]))
    
    print(f"\n  Gap columns: {gaps}")
    print(f"  Gap runs: {gap_runs}")
    
    # Characters are between gaps
    # Extract characters as segments between gaps
    text_cols = list(range(scan_start, scan_end))
    segments = []
    in_seg = False
    seg_start = 0
    
    for c in range(scan_start, scan_end):
        count = sum(mask[r, c] for r in body_rows)
        if count > 0 and not in_seg:
            seg_start = c
            in_seg = True
        elif count == 0 and in_seg:
            segments.append((seg_start, c - 1))
            in_seg = False
    if in_seg:
        segments.append((seg_start, c))
    
    print(f"\n  Character segments:")
    for i, (start, end) in enumerate(segments):
        width = end - start + 1
        print(f"\n  Segment {i}: cols {start}-{end} (width={width})")
        for r in body_rows:
            line = '    '
            for c in range(start, end + 1):
                line += '█' if mask[r, c] else '·'
            print(line)
