#!/usr/bin/env python3
"""Recover the deleted DKR-2 session and summarize its IMU and power data."""
import math
import gzip
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent
IMAGE = ROOT / 'dkr2_sd.img.gz'


def recover():
    with gzip.open(IMAGE, 'rb') as stream:
        image = stream.read()
    sector_size = struct.unpack_from('<H', image, 11)[0]
    sectors_per_cluster = image[13]
    reserved = struct.unpack_from('<H', image, 14)[0]
    fat_count = image[16]
    root_entries = struct.unpack_from('<H', image, 17)[0]
    sectors_per_fat = struct.unpack_from('<H', image, 22)[0]
    fat = image[reserved * sector_size:(reserved + sectors_per_fat) * sector_size]
    root = (reserved + fat_count * sectors_per_fat) * sector_size
    data = root + root_entries * 32
    cluster_size = sector_size * sectors_per_cluster

    def entry(name):
        for offset in range(root, data, 32):
            d = image[offset:offset + 32]
            if d[:11] == name:
                return struct.unpack_from('<H', d, 26)[0], struct.unpack_from('<I', d, 28)[0]
        raise ValueError(name)

    def cluster(number):
        return image[data + (number - 2) * cluster_size:
                     data + (number - 1) * cluster_size]

    def chain(first):
        while first < 0xFFF8:
            yield first
            first = struct.unpack_from('<H', fat, 2 * first)[0]

    power_first, power_length = entry(b'PWR0012 CSV')
    power_clusters = list(chain(power_first))
    power = b''.join(map(cluster, power_clusters))[:power_length]
    deleted_first, deleted_length = entry(b'\xe5MU0012 BIN')
    deleted_count = math.ceil(deleted_length / cluster_size)
    deleted_clusters = []
    i = deleted_first
    while len(deleted_clusters) < deleted_count:
        if struct.unpack_from('<H', fat, 2 * i)[0] == 0:
            deleted_clusters.append(i)
        i += 1
    recovered = b''.join(map(cluster, deleted_clusters))[:deleted_length]
    print('IMU clusters:', deleted_count, 'start:', deleted_first,
          'end:', deleted_clusters[-1], 'power clusters skipped:', len(power_clusters) - 1)
    print(recovered[:recovered.index(b'START\n') + 6].decode())
    return recovered, power


def parse_imu(blob):
    p = blob.index(b'START\n') + 6
    blocks = []
    samples = []
    while p < len(blob):
        magic = blob[p:p+2]
        if magic == b'\xa5T':
            p += 8
        elif magic == b'\xa5F':
            tick, count = struct.unpack_from('<IB', blob, p+2)
            end = p + 7 + count * 12
            if count == 0 or count > 32 or end > len(blob):
                break
            words = np.frombuffer(blob[p+7:end], dtype='<i2').reshape(count, 6)
            blocks.append((tick, count, p))
            for idx, values in enumerate(words):
                samples.append((tick, count - idx - 1, *values))
            p = end
        else:
            break
    print('parsed', len(blocks), 'FIFO blocks', len(samples), 'samples;',
          'first/last ticks', blocks[0][0], blocks[-1][0],
          'unparsed bytes', len(blob) - p)
    return np.array(samples, dtype=np.int64), np.array(blocks, dtype=np.int64)


def main():
    imu, power = recover()
    values, blocks = parse_imu(imu)
    (ROOT / 'IMU0012_recovered.BIN').write_bytes(imu)
    np.save(ROOT / 'IMU0012_samples.npy', values)
    powers = []
    for line in power.decode().splitlines()[2:]:
        t, volts, amps, temp = line.split(',')
        powers.append((int(t), float(volts), float(amps), float(temp)))
    powers = np.array(powers)
    # Adjacent low-voltage readings belong to the same pyro firing.
    dips = powers[powers[:,1] < 27][:,0]
    firings = [int(t) for i, t in enumerate(dips)
               if i == 0 or t - dips[i - 1] > 200]
    # REG AG 0x10 B8 means gyro FS = ±2000 dps: 70 mdps/LSB.
    # REG AG 0x20 A8 means accelerometer FS = ±16 g: 0.732 mg/LSB.
    ticks = blocks[:,0]
    starts = np.searchsorted(values[:,0], ticks)
    block_rates = np.add.reduceat(values[:,4], starts) / blocks[:,1]
    print('Firing  peak-g   gyro heading (clockwise)')
    headings = {}
    peaks = {}
    for anchor, fire in zip('CAB', firings):
        nearby = values[(values[:,0] >= fire - 200)&(values[:,0] <= fire + 2000)]
        peak = np.linalg.norm(nearby[:,5:8], axis=1).max() * .000732
        baseline = (ticks > fire - 5000) & (ticks < fire - 2000)
        bias = np.median(block_rates[baseline])
        motion = (ticks >= fire - 500) & (ticks <= fire + 2500)
        # The IMU +Z axis points up, so negative angular rate = clockwise.
        clockwise = -np.trapezoid((block_rates[motion] - bias) * .07,
                                  ticks[motion] / 1000)
        print(f'{anchor}: {peak:.1f} g, {clockwise:+.2f}°')
        headings[anchor] = clockwise
        peaks[anchor] = peak
    slipped = max(headings, key=lambda name: abs(headings[name]))
    print(f'GAIANSPACE{{{slipped}-{round(headings[slipped])}}}')


if __name__ == '__main__':
    main()
