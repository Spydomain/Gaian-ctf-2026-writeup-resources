import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')

# Cluster centers from KMeans(7):
# Class 0: Red=9  SWIR=47  (low red, low SWIR) - NORMAL
# Class 1: Red=21 SWIR=92  (high red, high SWIR) - NORMAL  
# Class 2: Red=8  SWIR=48  (low red, low SWIR) - NORMAL
# Class 3: Red=8  SWIR=98  (low red, HIGH SWIR) - ANOMALY!
# Class 4: Red=26 SWIR=97  (high red, high SWIR) - NORMAL
# Class 5: Red=25 SWIR=48  (high red, LOW SWIR) - ANOMALY!
# Class 6: Red=11 SWIR=57  (mid red, mid SWIR) - ambiguous

# The anomaly = SWIR inversion relative to what the Red channel predicts:
# - Low red (< ~15) normally has low SWIR (~47) → anomaly if SWIR is high (~98) = Class 3
# - High red (> ~20) normally has high SWIR (~95) → anomaly if SWIR is low (~48) = Class 5

# The TEXT = Class 3 | Class 5 in the KMeans labeling
# But the issue is that Class 3 and Class 5 also appear in background areas

# Let me re-examine: use the class map and look ONLY at the text region
pixels = tile.reshape(5, -1).T
kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
labels = kmeans.fit_predict(pixels.astype(float))
class_map = labels.reshape(128, 128)

# In the class map, which classes appear in the text region vs background?
print("=== Class distribution in text region (rows 35-70) ===")
for cls in range(7):
    text_count = np.sum((class_map[35:70, :] == cls))
    bg_count = np.sum((class_map[:35, :] == cls)) + np.sum((class_map[70:, :] == cls))
    print(f"  Class {cls}: text_region={text_count}, background={bg_count}")

# The text is painted using an INVERSION of the SWIR relative to what Red would predict
# Let me compute this explicitly
red = tile[0].astype(float)
swir = tile[4].astype(float)

# Compute expected SWIR from red channel
# Low red region: expected SWIR ~47
# High red region: expected SWIR ~97
# Use the actual cluster means for precision
expected_swir = np.where(red < 15, 47.0, 97.0)
inversion = swir - expected_swir  # positive = high when should be low, negative = low when should be high

# The text pixels will have |inversion| > 30 (they're off by ~50 from expected)
text_mask = (np.abs(inversion) > 30).astype(np.uint8)

print("\n=== Inversion-based text mask ===")
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

# Save this
scale = 16
region = text_mask[35:70, 10:80]
big = np.repeat(np.repeat(region * 255, scale, axis=0), scale, axis=1)
Image.fromarray(big, mode='L').save('final_inversion.png')
print("\nSaved final_inversion.png")

# Now try to ALSO combine with class map: text = inversion AND (class 3 or 5)
km_text = ((class_map == 3) | (class_map == 5)).astype(np.uint8)
combined = (text_mask & km_text)
region_c = combined[35:70, 10:80]
big_c = np.repeat(np.repeat(region_c * 255, scale, axis=0), scale, axis=1)
Image.fromarray(big_c, mode='L').save('final_combined_strict.png')
print("Saved final_combined_strict.png")

# Let me try a totally different approach: look at the raw SWIR difference 
# between each pixel and its surrounding area
# If a pixel is "text", its SWIR will be very different from its neighbors
from scipy import ndimage

# Local median SWIR
median_swir = ndimage.median_filter(swir, size=5)
local_diff = np.abs(swir.astype(float) - median_swir.astype(float))

# Render this
region_ld = local_diff[35:70, 10:80]
ld_norm = ((region_ld - region_ld.min()) / (region_ld.max() - region_ld.min()) * 255).astype(np.uint8)
big_ld = np.repeat(np.repeat(ld_norm, scale, axis=0), scale, axis=1)
Image.fromarray(big_ld, mode='L').save('final_local_diff.png')
print("Saved final_local_diff.png")

# For maximum clarity, try using a different channel combination
# Key observation: the text is at the INTERSECTION of where SWIR and NIR disagree  
# In normal vegetation: NIR is high, SWIR varies with moisture
# In the text: NIR and SWIR are decorrelated differently from background

# Actually let me try something completely different: 
# Look at which pixels have SWIR inverted relative to their Red channel
# More nuanced: fit a linear model of SWIR ~ f(Red) in background regions only
# Then the text pixels are outliers

# Simpler: just use the two-population model
# Population A: red < 15 → expected SWIR = ~47
# Population B: red >= 15 → expected SWIR = ~95

# Within each population, text pixels have SWIR swapped to the OTHER population's value
# So the signal is: for pop A pixels, text if SWIR > 70; for pop B pixels, text if SWIR < 70

pop_a = (red < 15)  # low red
pop_b = ~pop_a       # high red

text_a = (pop_a & (swir > 70)).astype(np.uint8)  # low red but high SWIR
text_b = (pop_b & (swir < 70)).astype(np.uint8)  # high red but low SWIR
text_combined = (text_a | text_b)

print("\n=== Population-based text detection ===")
for r in range(35, 70):
    line = ''
    has_text = False
    for c in range(10, 80):
        if text_combined[r, c]:
            line += '█'
            has_text = True
        else:
            line += '·'
    if has_text:
        print(f'{r}: {line}')

region_p = text_combined[35:70, 10:80]
big_p = np.repeat(np.repeat(region_p * 255, scale, axis=0), scale, axis=1)
Image.fromarray(big_p, mode='L').save('final_population.png')
print("\nSaved final_population.png")

# Save individual lines with the population method at 24x
lines = [
    ("pop_line1", 36, 44, 10, 78),
    ("pop_line2", 47, 56, 12, 78),
    ("pop_line3", 59, 68, 22, 68),
]

for name, y0, y1, x0, x1 in lines:
    region = text_combined[y0:y1, x0:x1]
    sc = 24
    big = np.repeat(np.repeat(region * 255, sc, axis=0), sc, axis=1)
    Image.fromarray(big, mode='L').save(f'final_{name}.png')
    print(f"\nSaved final_{name}.png")
    for r in range(y0, y1):
        line = ''
        for c in range(x0, x1):
            line += '█' if text_combined[r, c] else '·'
        print(f'  {r}: {line}')
