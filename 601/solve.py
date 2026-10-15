#!/usr/bin/env python3
"""Read the RTSP SDP service name from the Mars downlink capture."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
capture = (ROOT / 'mars_downlink.pcap').read_bytes()
match = re.search(rb'RTSP/1\.0 200 OK\r\n(?:(?!\r\n\r\n).)*\r\n\r\nv=0\r\n.*?\r\ns=(GAIANSPACE\{[^}]+\})\r\n',
                  capture, re.DOTALL)
assert match
print('SDP service name:', match[1].decode())
