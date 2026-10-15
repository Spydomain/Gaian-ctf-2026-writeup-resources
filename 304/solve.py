#!/usr/bin/env python3
"""Verify the five Gerber-review answers and open the server's sealed flag."""
from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import server  # noqa: E402  The supplied challenge service.

# In server order: copper layers, long edge (mm), 4-pad sensor,
# exposed debug label, main MCU pad count.
answers = ['2', '50', 'u2', 'swd', '6']
for answer, (_, expected_hash) in zip(answers, server.QUESTIONS):
    assert hashlib.sha256(answer.encode()).hexdigest() == expected_hash
flag = server.unseal(answers)
assert flag.startswith('GAIANSPACE{') and flag.endswith('}')
print('Gerber answers:', '|'.join(answers))
print(flag)
