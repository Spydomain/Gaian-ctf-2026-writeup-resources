import numpy as np
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')

# Let me look at the raw 5-channel data for each character position in line 3
# to understand what's happening at the pixel level

# We're using: red < 15 → expect SWIR low → text if SWIR high
#              red >= 15 → expect SWIR high → text if SWIR low

red = tile[0]
swir = tile[4]

print("="*60)
print("LINE 3 RAW DATA ANALYSIS")
print("="*60)

# For each character, show Red and SWIR values
for ci in range(7):
    cs = 24 + ci * 6
    print(f"\nChar {ci} (cols {cs}-{cs+4}), body rows 61-66:")
    print(f"  Red values:")
    for r in range(61, 67):
        vals = red[r, cs:cs+5]
        print(f"    {r}: " + " ".join(f"{v:3d}" for v in vals))
    print(f"  SWIR values:")
    for r in range(61, 67):
        vals = swir[r, cs:cs+5]
        print(f"    {r}: " + " ".join(f"{v:3d}" for v in vals))
    
    # Show the "expected" vs actual behavior
    print(f"  Population & text detection:")
    for r in range(61, 67):
        line = ''
        for c in range(cs, cs+5):
            rv = red[r, c]
            sv = swir[r, c]
            if rv < 15:
                # Low red population
                if sv > 70:
                    line += 'A'  # Anomaly (low red, high SWIR)
                else:
                    line += '·'  # Normal (low red, low SWIR)
            else:
                # High red population
                if sv < 70:
                    line += 'B'  # Anomaly (high red, low SWIR)
                else:
                    line += '·'  # Normal (high red, high SWIR)
        print(f"    {r}: {line} (A=lowR/hiSW, B=hiR/loSW)")
    
    # Also show the green channel for additional info
    green = tile[1]
    blue = tile[2]
    nir = tile[3]
    
    # Show all channels for better understanding
    print(f"  All 5 channels (R,G,B,NIR,SWIR):")
    for r in range(61, 67):
        row_str = '    '
        for c in range(cs, cs+5):
            row_str += f"({red[r,c]:2d},{green[r,c]:2d},{blue[r,c]:2d},{nir[r,c]:3d},{swir[r,c]:3d}) "
        print(f"    {r}: {row_str}")

# Let me also check: what if the red threshold should be different?
# Maybe 15 is too aggressive. Let me try different thresholds
print("\n\n" + "="*60)
print("TESTING DIFFERENT RED THRESHOLDS")
print("="*60)

for thresh in [12, 14, 15, 16, 18, 20]:
    pop_a = (tile[0].astype(float) < thresh)
    pop_b = ~pop_a
    swir_f = tile[4].astype(float)
    text_a = (pop_a & (swir_f > 70)).astype(np.uint8)
    text_b = (pop_b & (swir_f < 70)).astype(np.uint8)
    text = text_a | text_b
    
    print(f"\nRed threshold = {thresh}:")
    print(f"  Line 3 body (rows 61-66):")
    for r in range(61, 67):
        line = ''
        for c in range(22, 68):
            line += '█' if text[r, c] else '·'
        print(f"    {r}: {line}")
