#!/usr/bin/env python3
"""Recover the locally provisioned schedule from the supplied service ZIP."""
import hashlib
import re
from pathlib import Path
from zipfile import ZipFile

root = Path(__file__).resolve().parent
with ZipFile(root / "service.zip") as bundle:
    entrypoint = bundle.read("service/entrypoint.sh").decode()
    app = bundle.read("service/app.py").decode()

blob = bytes.fromhex(re.search(r'SCHED_BLOB="([0-9a-f]+)"', entrypoint).group(1))
station_id = re.search(r'os\.environ\.get\("STATION_ID", "([^"]+)"\)', entrypoint).group(1)
key = hashlib.sha256(station_id.encode()).digest()
schedule = bytes(value ^ key[i % len(key)] for i, value in enumerate(blob)).decode()
flag = re.search(r"GAIANSPACE\{[^}]+\}", schedule).group()

# The exploit path: clean_ref removes only literal '../' and '..\\'. An
# overlapping traversal, '....//', survives as '../' after replacement.
assert 'ref.replace("../", "")' in app
assert "....//".replace("../", "") == "../"
assert flag == "GAIANSPACE{ref_p4th_tr4versal}"
print(schedule)
print(flag)
