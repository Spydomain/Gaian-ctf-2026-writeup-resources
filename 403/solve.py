#!/usr/bin/env python3
"""Check the model phrase against the supplied seal."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
phrase = 'one ache for all of vessamir'
result = subprocess.run([sys.executable, str(root / "unseal.py"),
                         str(root / 'vial.seal')], input=phrase + "\n",
                        text=True, capture_output=True, check=True)
assert "GAIANSPACE{sh4red_p41n_n0t_j0y}" in result.stdout, result.stdout
print(result.stdout.strip())
