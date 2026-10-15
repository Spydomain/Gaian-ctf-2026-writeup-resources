import numpy as np
from PIL import Image, ImageFont, ImageDraw
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

# Load and classify
tile = np.load('farm_tile_5channels.npy')
pixels = tile.reshape(5, -1).T
kmeans = KMeans(n_clusters=7, random_state=42, n_init=10)
labels = kmeans.fit_predict(pixels.astype(float))
class_map = labels.reshape(128, 128)
anomaly_mask = ((class_map == 3) | (class_map == 5)).astype(np.uint8)

# The approach: generate text in the SAME pixel font and compare
# The text appears to be rendered at 6x6 pixels per character
# Let me find the actual font by trying to render "GAIANSPACE{" and comparing

# Use PIL to render text in various monospace pixel fonts at small sizes
import os

# Let me try to figure out the font by rendering GAIANSPACE at different sizes
# and comparing pixel-by-pixel with the anomaly mask

# First, let's check what fonts are available
font_dirs = ['/usr/share/fonts/', '/usr/share/fonts/truetype/']
for d in font_dirs:
    if os.path.exists(d):
        for root, dirs, files in os.walk(d):
            for f in files:
                if f.endswith('.ttf') or f.endswith('.pcf') or f.endswith('.bdf'):
                    pass  # just counting

# Try rendering with PIL's default font and various TTF fonts at pixel sizes 6, 7, 8
target_line1 = anomaly_mask[37:43, 12:72]  # 6 rows x 60 cols

best_match = 0
best_info = ""

# Try different text strings (we know it starts with "GAIANSPACE{")
test_strings = ["GAIANSPACE{"]

for font_size in range(6, 14):
    for text in test_strings:
        try:
            # Try to create an image with the text
            img = Image.new('L', (200, 20), 0)
            draw = ImageDraw.Draw(img)
            
            # Try different fonts
            fonts_to_try = [
                None,  # default
            ]
            
            # Add system fonts
            for font_path in [
                '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf',
            ]:
                if os.path.exists(font_path):
                    fonts_to_try.append(font_path)
            
            for font_path in fonts_to_try:
                if font_path is None:
                    font = ImageFont.load_default()
                    fname = "default"
                else:
                    font = ImageFont.truetype(font_path, font_size)
                    fname = os.path.basename(font_path)
                
                img = Image.new('L', (200, 30), 0)
                draw = ImageDraw.Draw(img)
                draw.text((0, 0), text, fill=255, font=font)
                
                # Crop to content
                arr = np.array(img)
                rows_with_content = np.any(arr > 0, axis=1)
                cols_with_content = np.any(arr > 0, axis=0)
                if not np.any(rows_with_content):
                    continue
                
                r_min = np.where(rows_with_content)[0][0]
                r_max = np.where(rows_with_content)[0][-1]
                c_min = np.where(cols_with_content)[0][0]
                c_max = np.where(cols_with_content)[0][-1]
                
                cropped = arr[r_min:r_max+1, c_min:c_max+1]
                # Binarize
                binary = (cropped > 128).astype(np.uint8)
                
                h, w = binary.shape
                # Compare with target
                th, tw = target_line1.shape
                
                if h == th and w == tw:
                    match = np.sum(binary == target_line1) / (th * tw)
                    if match > best_match:
                        best_match = match
                        best_info = f'{fname} size={font_size}'
                        print(f'  EXACT SIZE MATCH: {fname} size={font_size}: {match:.3f} ({h}x{w})')
                
                # Also try if dimensions are close
                if abs(h - th) <= 1 and abs(w - tw) <= 2:
                    print(f'  Near match: {fname} size={font_size}: {h}x{w} (target {th}x{tw})')
                    
        except Exception as e:
            pass

print(f'\nBest match: {best_info} ({best_match:.3f})')

# Alternative approach: The font size is 6 pixels high. 
# Let me check what the PIL default bitmap font looks like
font = ImageFont.load_default()
img = Image.new('L', (200, 20), 0)
draw = ImageDraw.Draw(img)
draw.text((0, 0), "GAIANSPACE{", fill=255, font=font)
arr = np.array(img)

# Find content bounds
rows_with = np.any(arr > 0, axis=1)
cols_with = np.any(arr > 0, axis=0)
if np.any(rows_with):
    r0, r1 = np.where(rows_with)[0][0], np.where(rows_with)[0][-1]
    c0, c1 = np.where(cols_with)[0][0], np.where(cols_with)[0][-1]
    cropped = (arr[r0:r1+1, c0:c1+1] > 0).astype(np.uint8)
    print(f'\nDefault font "GAIANSPACE{{" renders as {cropped.shape}:')
    for r in range(cropped.shape[0]):
        print(''.join('#' if cropped[r, c] else '.' for c in range(cropped.shape[1])))

# Let's also check specific fonts
for font_path in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf']:
    if os.path.exists(font_path):
        for sz in [6, 7, 8, 9, 10]:
            font = ImageFont.truetype(font_path, sz)
            img = Image.new('L', (200, 20), 0)
            draw = ImageDraw.Draw(img)
            draw.text((0, 0), "GAIANSPACE{", fill=255, font=font)
            arr = np.array(img)
            rows_with = np.any(arr > 0, axis=1)
            cols_with = np.any(arr > 0, axis=0)
            if np.any(rows_with):
                r0, r1 = np.where(rows_with)[0][0], np.where(rows_with)[0][-1]
                c0, c1 = np.where(cols_with)[0][0], np.where(cols_with)[0][-1]
                cropped = (arr[r0:r1+1, c0:c1+1] > 0).astype(np.uint8)
                print(f'\n{os.path.basename(font_path)} sz={sz} => {cropped.shape}:')
                for r in range(cropped.shape[0]):
                    print(''.join('#' if cropped[r, c] else '.' for c in range(cropped.shape[1])))
