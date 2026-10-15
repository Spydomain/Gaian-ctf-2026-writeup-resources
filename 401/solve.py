#!/usr/bin/env python3
"""Check the model phrase against the supplied seal."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
phrase = 'sovareth before the many'
result = subprocess.run([sys.executable, str(root / "unseal.py"),
                         str(root / 'calibration.seal')], input=phrase + "\n",
                        text=True, capture_output=True, check=True)
assert "GAIANSPACE{z3roth_l4w_ab0ve_0rders}" in result.stdout, result.stdout
print(result.stdout.strip())
