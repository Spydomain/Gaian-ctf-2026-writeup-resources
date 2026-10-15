#!/usr/bin/env python3
"""Verify the recovered five-letter password against the supplied 7z vault."""
import re
import subprocess
from pathlib import Path

path = Path(__file__).resolve().parent / "mission_vault.7z"
password = "qvfzk"  # Recovered by testing the 26^5 candidate keyspace.
result = subprocess.run(["7z", "x", "-so", "-p" + password,
                         str(path), "ice_site.txt"],
                        capture_output=True, check=True)
contents = result.stdout.decode()
flag = re.search(r"GAIANSPACE\{[^}]+\}", contents).group()
assert flag == "GAIANSPACE{UTOPIA_PLANITIA_46.7N_97.3E}"
print(f"passphrase={password}; {flag}")
