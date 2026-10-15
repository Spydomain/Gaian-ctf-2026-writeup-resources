#!/usr/bin/env python3
"""Locate the claim-batch transmitter from four matched gateway timestamps."""
import base64
import csv
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parent
C = 299_792_458.0


def packet_forwarder(site):
    packets = {}
    for line in (ROOT / f'gw_{site}_pktfwd.log').read_text().splitlines():
        if 'JSON up: ' not in line:
            continue
        for row in json.loads(line.split('JSON up: ', 1)[1])['rxpk']:
            payload = base64.b64decode(row['data'])
            if row['stat'] == 1 and payload.startswith(b'\xb7\x2a'):
                packets[payload.hex()] = int(row['ftime'])
    return packets


def tower_export():
    with (ROOT / 'gw_tower_export.csv').open() as stream:
        rows = csv.DictReader(line for line in stream if not line.startswith('#'))
        return {row['payload_hex']: int(row['fine_ns']) for row in rows
                if row['crc'] == 'OK' and row['payload_hex'].startswith('b72a')}


def project(lon, lat, eov=False):
    source = ['EPSG:23700'] if eov else ['+proj=longlat', '+datum=WGS84']
    command = ['cs2cs', '-f', '%.5f', *source, '+to', '+proj=utm', '+zone=34', '+datum=WGS84']
    result = subprocess.check_output(command, input=f'{lon} {lat}\n'.encode()).decode()
    return np.array([float(x) for x in result.split()[:2]])


def main():
    times = {site: packet_forwarder(site) for site in ('dryer', 'silo', 'pivot7')}
    times['tower'] = tower_export()
    names = ('dryer', 'silo', 'tower', 'pivot7')
    common = sorted(set.intersection(*(set(times[name]) for name in names)))
    assert len(common) >= 20
    observations = np.array([[times[name][payload] for name in names] for payload in common], float)
    relative_ns = np.median(observations - observations[:, [0]], axis=0)

    locations = {}
    with (ROOT / 'coop_gateways.csv').open() as stream:
        for row in csv.DictReader(stream):
            if row['site'].lower() in names:
                locations[row['site'].lower()] = project(float(row['lon']), float(row['lat']))
    match = re.search(r'EOV Y ([\d.]+)\s+X ([\d.]+)',
                      (ROOT / 'coop_worklog.txt').read_text())
    assert match
    locations['pivot7'] = project(float(match[1]), float(match[2]), eov=True)
    sites = np.array([locations[name] for name in names])

    def residual(position):
        travel_ns = np.linalg.norm(sites - position, axis=1) / C * 1e9
        return relative_ns - (travel_ns - travel_ns[0])

    result = least_squares(residual, sites.mean(axis=0))
    assert np.max(np.abs(result.fun)) < 200, result.fun
    point = Point(result.x)
    parcels = json.loads((ROOT / 'parcels.geojson').read_text())['features']
    matches = [row['properties']['parcel'] for row in parcels if shape(row['geometry']).covers(point)]
    assert len(matches) == 1, matches
    print('Matched packets:', len(common))
    print('Median relative arrival times (ns):', relative_ns.tolist())
    print('Position (UTM 34N):', result.x.tolist())
    print('TDOA residuals (ns):', result.fun.tolist())
    print('GAIANSPACE{' + matches[0] + '}')


if __name__ == '__main__':
    main()
