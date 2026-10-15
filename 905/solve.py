#!/usr/bin/env python3
"""Recover the missing orbital-day fraction and decrypt the sealed park token."""
import hashlib
import hmac
import json
import re
import struct
from pathlib import Path
from zipfile import ZipFile

root = Path(__file__).resolve().parent
orders = [json.loads(line) for line in (root / "signed_cmds.log").read_text().splitlines()
          if line.startswith("{")]
assert len(orders) == 3
first = orders[0]
message = (f"{first['station_id']}|{first['action']}|"
           f"{first['angle_deg']}|{first['nonce']}").encode()

matches = []
for width in range(1, 7):
    for number in range(10 ** width):
        epoch = f"26278.{number:0{width}d}"
        key = hashlib.sha256(f"{first['station_id']}:{epoch}".encode()).digest()
        if hmac.compare_digest(hmac.new(key, message, hashlib.sha256).hexdigest(),
                               first["sig"]):
            matches.append((epoch, key))
    if matches:
        break
assert len(matches) == 1, matches
epoch, key = matches[0]

for order in orders:
    canon = f"{order['station_id']}|{order['action']}|{order['angle_deg']}|{order['nonce']}"
    assert hmac.compare_digest(hmac.new(key, canon.encode(), hashlib.sha256).hexdigest(),
                               order["sig"])

with ZipFile(root / "service.zip") as bundle:
    ciphertext = bundle.read("service/flag.enc")
stream = b"".join(hmac.new(key, b"SLEW-CTR" + struct.pack(">I", index),
                           hashlib.sha256).digest()
                  for index in range((len(ciphertext) + 31) // 32))
plaintext = bytes(byte ^ stream[index] for index, byte in enumerate(ciphertext)).decode()
flag = re.fullmatch(r"GAIANSPACE\{[^}]+\}", plaintext).group()
assert flag == "GAIANSPACE{f0rged_slew_t0_h0me}"
print(f"TLE_EPOCH={epoch}; all {len(orders)} signatures match; {flag}")
