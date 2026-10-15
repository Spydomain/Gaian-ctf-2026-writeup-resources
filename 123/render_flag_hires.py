import numpy as np
from PIL import Image, ImageFont, ImageDraw
import warnings
warnings.filterwarnings('ignore')

tile = np.load('farm_tile_5channels.npy')
# Shape: (5, 128, 128) - 5 channels, 128x128

# Let's look at this differently. The text in the zoomed image shows characters
# that look like they could be read. Let me look at the actual image that was 
# generated as clean_flag_text.png - let me look at how it was generated.

# Going back to first principles: The task says "ISODATA with 7 classes"
# and to "count what actually grows here"
# The flag format is GAIANSPACE{...}

# Let me look at the isodata_7class.png which showed visible text
# The text was clearly visible in the CLASS MAP itself!
# So the flag is encoded by using different land cover classes to "paint" letters

# Let me use the combined (class 3 | class 5) mask as a filled text image
# and try to read it directly with better rendering

from sklearn.cluster import KMeans

pixels = tile.reshape(5, -1).T
kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
labels = kmeans.fit_predict(pixels.astype(float))
class_map = labels.reshape(128, 128)

# The text IS the anomaly class (3 + 5) - it's written in a pixel font
# Let me render this at maximum quality
anomaly_mask = ((class_map == 3) | (class_map == 5)).astype(np.uint8)

# Extract just the text rows and scale up massively
for line_name, y0, y1 in [("Line1", 36, 44), ("Line2", 47, 55), ("Line3", 59, 68)]:
    sub = anomaly_mask[y0:y1, :]
    # Scale 16x
    big = np.repeat(np.repeat(sub * 255, 16, axis=0), 16, axis=1)
    Image.fromarray(big).save(f'flag_{line_name}_16x.png')
    print(f'Saved flag_{line_name}_16x.png ({big.shape})')

# Also do the WHOLE text region at 12x
text_region = anomaly_mask[35:70, 10:80]
big = np.repeat(np.repeat(text_region * 255, 12, axis=0), 12, axis=1)
Image.fromarray(big).save('flag_all_12x.png')
print(f'Saved flag_all_12x.png ({big.shape})')

# Now let me try a completely different approach: 
# Maybe the text is just one class, not two
# Class 3 center: [8, 15, 9, 107, 97] (high NIR+SWIR) 
# Class 5 center: [25, 32, 44, 63, 47] (moderate all)
# These are very different spectral signatures, which suggests 
# maybe one is the actual text and the other is just noise/edge effect

# Let me try individual class maps at high res
for cls_id in [3, 5]:
    mask = (class_map == cls_id).astype(np.uint8)
    text_region = mask[35:70, 10:80]
    big = np.repeat(np.repeat(text_region * 255, 12, axis=0), 12, axis=1)
    Image.fromarray(big).save(f'flag_class{cls_id}_12x.png')
    print(f'Saved flag_class{cls_id}_12x.png')
