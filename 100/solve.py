#!/usr/bin/env python3
"""Recover the welcome check-in from the saved challenge description."""
from pathlib import Path
import re

prompt = Path(__file__).resolve().parents[1] / 'challenge_prompts' / '100.txt'
text = prompt.read_text()
word = re.search(r'The word on the pad is ([A-Za-z]+)\.', text).group(1)
assert 'GAIANSPACE{[Welcome]}' in text
assert word == 'Welcome'
print(f'GAIANSPACE{{{word}}}')
