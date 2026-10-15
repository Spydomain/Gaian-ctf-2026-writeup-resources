#!/usr/bin/env python3
"""Check the model phrase against the supplied seal."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
phrase = 'only the kessaly remains'
result = subprocess.run([sys.executable, str(root / "unseal.py"),
                         str(root / 'machine.seal')], input=phrase + "\n",
                        text=True, capture_output=True, check=True)
assert "GAIANSPACE{n0thing_fr0m_st0ck}" in result.stdout, result.stdout
print(result.stdout.strip())
