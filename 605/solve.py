#!/usr/bin/env python3
"""Carve flight 7 beyond its stale FAT file length and inspect gyro clipping."""
import gzip
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent
with gzip.open(ROOT / 'bbx_sd.img.gz', 'rb') as stream:
    disk = stream.read()

sector = struct.unpack_from('<H', disk, 11)[0]
reserved = struct.unpack_from('<H', disk, 14)[0]
fats = disk[16]
fat_sectors = struct.unpack_from('<H', disk, 22)[0]
root_count = struct.unpack_from('<H', disk, 17)[0]
root = (reserved + fats * fat_sectors) * sector
data = root + root_count * 32
cluster_size = sector * disk[13]
for pos in range(root, data, 32):
    entry = disk[pos:pos + 32]
    if entry[:11] == b'BBX0007 BIN':
        first_cluster = struct.unpack_from('<H', entry, 26)[0]
        directory_size = struct.unpack_from('<I', entry, 28)[0]
        break
else:
    raise ValueError('BBX0007.BIN not found')

base = data + (first_cluster - 2) * cluster_size
start = disk.index(b'START\n', base) + 6
p = start
blocks = []
while p + 8 <= len(disk):
    kind = disk[p:p + 2]
    if kind == b'\xa5T':
        p += 8
        continue
    if kind != b'\xa5F':
        break
    tick, n = struct.unpack_from('<IB', disk, p + 2)
    end = p + 7 + 12 * n
    if not 1 <= n <= 32 or end > len(disk):
        break
    samples = np.frombuffer(disk[p + 7:end], dtype='<i2').reshape(n, 6)
    blocks.append((tick, samples))
    p = end

first_clip = next(tick for tick, samples in blocks
                  if np.any((samples[:, :3] == -32768) |
                            (samples[:, :3] == 32767)))

def median_gx(low, high):
    return float(np.median(np.concatenate(
        [s[:, 0] for tick, s in blocks if low <= tick < high])))


def median_gy(low, high):
    return float(np.median(np.concatenate(
        [s[:, 1] for tick, s in blocks if low <= tick < high])))


def median_ay(low, high):
    return float(np.median(np.concatenate(
        [s[:, 4] for tick, s in blocks if low <= tick < high])))


print('Directory size:', directory_size, 'carved bytes:', p - base)
print('Known forward lean gyro X:', median_gx(60300, 62500),
      'return to level gyro X:', median_gx(63800, 64500))
assert median_gx(60300, 62500) > 0
assert median_gx(63800, 64500) < 0
assert median_ay(60300, 62500) < 0
# During the known nose-down lean, negative accel Y identifies IMU +Y as
# pointing forward. With +Z up, the right-handed board has +X to the right.
# At fault onset (before controller reaction changes gyro X's sign), negative
# gyro Y tips the craft left, while negative gyro X tips it forward.
fault_x = median_gx(78700, 78739)
fault_y = median_gy(78700, 78739)
assert fault_x < 0 and fault_y < 0
assert first_clip == 78758
servo = 3  # Front left is S3 in drone_config.md.
flag = f'GAIANSPACE{{S{servo}-T{first_clip}}}'
assert flag == 'GAIANSPACE{S3-T78758}'
print('Fault-onset gyro X/Y:', fault_x, fault_y,
      'first clipped block:', first_clip)
print(flag)
