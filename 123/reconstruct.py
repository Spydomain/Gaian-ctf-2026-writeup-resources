import re
import numpy as np
from PIL import Image

# Parse frames from all_frames.txt
frames = []
with open('all_frames.txt', 'r') as f:
    lines = f.readlines()

i = 0
while i < len(lines):
    line = lines[i].strip()
    if line.startswith('FRAME:'):
        m = re.match(r'FRAME: len=(\d+), phy_crc_ok=(\d+), app_crc_ok=(\d+), app_crc=([0-9a-f]+)/([0-9a-f]+)', line)
        if m:
            length = int(m.group(1))
            phy_crc = int(m.group(2))
            app_crc_ok = int(m.group(3))
            app_crc = int(m.group(4), 16)
            calc_crc = int(m.group(5), 16)
            
            if i + 1 < len(lines):
                hex_line = lines[i + 1].strip()
                hex_bytes = hex_line.split()
                if len(hex_bytes) == length:
                    data = bytes(int(b, 16) for b in hex_bytes)
                    frames.append({
                        'length': length,
                        'phy_crc_ok': phy_crc,
                        'app_crc_ok': app_crc_ok,
                        'app_crc': app_crc,
                        'calc_crc': calc_crc,
                        'data': data
                    })
                    i += 1
    i += 1

# Process 91-byte frames (assume 4-byte header + 2-byte CRC = 85 bytes payload)
frames_91 = [f for f in frames if f['length'] == 91]

# Extract layer and line info
# Byte0: layer (0x34, 0x44, 0x54, 0x64, 0x74) -> map to 0-4
# Byte1: line_high (0x01, 0x11, ..., 0xf1) -> high nibble 0-15
# Byte2: line_low (0xe0-0xe7, 0xf0-0xf7) -> high nibble 0xe/0xf (0/1), low nibble 0-7

layer_map = {0x34: 0, 0x44: 1, 0x54: 2, 0x64: 3, 0x74: 4}

images = {}
for f in frames_91:
    d = f['data']
    b0, b1, b2 = d[0], d[1], d[2]
    
    if b0 not in layer_map:
        continue
    layer = layer_map[b0]
    
    line_high = (b1 >> 4) & 0xF  # 0-15
    line_low_high = (b2 >> 4) & 0xF  # 0xE or 0xF -> 0 or 1
    line_low_low = b2 & 0xF  # 0-7
    
    line = line_high * 16 + line_low_high * 8 + line_low_low  # 0-255
    
    # Payload: bytes 4 to -3 (excluding 4-byte header and 2-byte CRC)
    payload = d[4:-2]
    
    if len(payload) != 85:
        print(f'Warning: payload len {len(payload)} for layer {layer} line {line}')
        continue
    
    if layer not in images:
        images[layer] = {}
    images[layer][line] = payload

print('Layer coverage:')
for layer in sorted(images.keys()):
    lines_present = sorted(images[layer].keys())
    print(f'  Layer {layer}: {len(lines_present)} lines, range {lines_present[0]}-{lines_present[-1]}')

# Reconstruct images (256 lines x 85 columns)
for layer in sorted(images.keys()):
    img = np.zeros((256, 85), dtype=np.uint8)
    for line in range(256):
        if line in images[layer]:
            img[line, :] = np.frombuffer(images[layer][line], dtype=np.uint8)
        else:
            img[line, :] = 0  # missing lines as black
    
    # Save as PNG
    Image.fromarray(img).save(f'layer_{layer}.png')
    print(f'Saved layer_{layer}.png ({img.shape})')
    
    # Also save as raw
    img.tofile(f'layer_{layer}.raw')

# Check 171-byte frames
frames_171 = [f for f in frames if f['length'] == 171]
print(f'\n171-byte frames: {len(frames_171)}')
# Assume header: byte0=0x93 (fixed), byte1=sub-layer, byte2=line, byte3=?, byte4=?
# Payload: 171 - 5 - 2 = 164 bytes?
# Or different header structure

# Check 58-byte frames
frames_58 = [f for f in frames if f['length'] == 58]
frames_59 = [f for f in frames if f['length'] == 59]
print(f'58-byte frames: {len(frames_58)}')
print(f'59-byte frames: {len(frames_59)}')