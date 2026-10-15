#!/usr/bin/env python3
"""Inspect the exfiltrated Gerber archive's fabrication note."""
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent
with zipfile.ZipFile(ROOT / 'foundation_one_gerbers.zip') as archive:
    members = [name for name in archive.namelist() if name.endswith('-F_Silkscreen.gbr')]
    assert len(members) == 1
    silkscreen = archive.read(members[0])
match = re.search(rb'G04 FAB-NOTE[^\r\n]*?(GAIANSPACE\{[^}]+\})', silkscreen)
assert match
print('Archive member:', members[0])
print(match[1].decode())
