#!/usr/bin/env python3
"""Check the model phrase against the supplied seal."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
phrase = 'orvanthe burns for home'
result = subprocess.run([sys.executable, str(root / "unseal.py"),
                         str(root / 'burn.seal')], input=phrase + "\n",
                        text=True, capture_output=True, check=True)
assert "GAIANSPACE{3very_gr41n_c0unts}" in result.stdout, result.stdout
print(result.stdout.strip())
