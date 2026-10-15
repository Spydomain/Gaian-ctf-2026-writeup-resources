import re

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

print(f'Total frames parsed: {len(frames)}')

frames_91 = [f for f in frames if f['length'] == 91]
frames_171 = [f for f in frames if f['length'] == 171]
frames_58 = [f for f in frames if f['length'] == 58]
frames_59 = [f for f in frames if f['length'] == 59]

print(f'91-byte frames: {len(frames_91)}')
print(f'171-byte frames: {len(frames_171)}')
print(f'58-byte frames: {len(frames_58)}')
print(f'59-byte frames: {len(frames_59)}')

# Analyze 171-byte frames
print(f'\n171-byte frames: {len(frames_171)}')
print('\nFirst 20 frames:')
for i, f in enumerate(frames_171[:20]):
    d = f['data']
    print(f'  Frame {i}: 0x{d[0]:02x} 0x{d[1]:02x} 0x{d[2]:02x} 0x{d[3]:02x} 0x{d[4]:02x} | len={len(d)}')

# First byte values
first_bytes = [f['data'][0] for f in frames_171]
print(f'\nFirst byte values: {sorted(set(first_bytes))}')
for b in sorted(set(first_bytes)):
    count = first_bytes.count(b)
    print(f'  0x{b:02x}: {count}')

# Second byte
second_bytes = [f['data'][1] for f in frames_171]
print(f'\nSecond byte values: {sorted(set(second_bytes))}')
for b in sorted(set(second_bytes)):
    count = second_bytes.count(b)
    print(f'  0x{b:02x}: {count}')

# Third byte
third_bytes = [f['data'][2] for f in frames_171]
print(f'\nThird byte values: {sorted(set(third_bytes))}')
for b in sorted(set(third_bytes)):
    count = third_bytes.count(b)
    print(f'  0x{b:02x}: {count}')

# Analyze 58-byte frames
print(f'\n\n58-byte frames: {len(frames_58)}')
for i, f in enumerate(frames_58):
    d = f['data']
    print(f'  Frame {i}: 0x{d[0]:02x} 0x{d[1]:02x} 0x{d[2]:02x} 0x{d[3]:02x} | len={len(d)}')

# Analyze 59-byte frames
print(f'\n59-byte frames: {len(frames_59)}')
for i, f in enumerate(frames_59):
    d = f['data']
    print(f'  Frame {i}: 0x{d[0]:02x} 0x{d[1]:02x} 0x{d[2]:02x} 0x{d[3]:02x} | len={len(d)}')