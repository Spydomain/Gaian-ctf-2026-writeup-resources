import numpy as np
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')
swir = tile[4]  # shape (128, 128)

# Simple threshold: SWIR > 70 = text, SWIR <= 70 = background
# The values cluster around 46 and 97, so any threshold between 60-80 works
text_mask = (swir > 70).astype(np.uint8)

scale = 16
# Full text region
region = text_mask[35:70, 10:80]
big = np.repeat(np.repeat(region * 255, scale, axis=0), scale, axis=1)
Image.fromarray(big, mode='L').save('final_swir70.png')
print("Saved final_swir70.png")

# Print ASCII art for ALL lines
print("\n=== SWIR > 70 TEXT (clean binary) ===")
for r in range(35, 70):
    line = ''
    has_text = False
    for c in range(10, 80):
        if text_mask[r, c]:
            line += '█'
            has_text = True
        else:
            line += '·'
    if has_text:
        print(f'{r}: {line}')
    else:
        print(f'{r}: (empty)')

# Save individual lines at 24x
lines = [
    ("line1", 36, 44, 10, 78),
    ("line2", 47, 56, 12, 78),
    ("line3", 59, 68, 22, 68),
]

for name, y0, y1, x0, x1 in lines:
    region = text_mask[y0:y1, x0:x1]
    sc = 24
    big = np.repeat(np.repeat(region * 255, sc, axis=0), sc, axis=1)
    Image.fromarray(big, mode='L').save(f'final_{name}.png')
    print(f"\nSaved final_{name}.png")
    for r in range(y0, y1):
        line = ''
        for c in range(x0, x1):
            line += '█' if text_mask[r, c] else '·'
        print(f'  {r}: {line}')

# Also create a version where we use SWIR as continuous grayscale with high contrast
# Map: SWIR < 60 -> black (0), SWIR > 80 -> white (255), middle -> linear
swir_f = swir.astype(float)
contrast = np.clip((swir_f - 60) / (80 - 60), 0, 1) * 255
contrast_u8 = contrast.astype(np.uint8)
region_c = contrast_u8[35:70, 10:80]
big_c = np.repeat(np.repeat(region_c, scale, axis=0), scale, axis=1)
Image.fromarray(big_c, mode='L').save('final_contrast.png')
print("\nSaved final_contrast.png (high-contrast continuous)")
