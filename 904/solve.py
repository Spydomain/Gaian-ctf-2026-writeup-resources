#!/usr/bin/env python3
"""Read the two nameplate constants from the maintenance client's code."""
import re
import subprocess
from pathlib import Path

binary = Path(__file__).resolve().parent / "gotox-maint"
disassembly = subprocess.check_output(
    ["objdump", "-d", "-Mintel", str(binary)], text=True)
first = int(re.search(r"mov\s+r8d,0x([0-9a-f]+)", disassembly).group(1), 16)
second = int(re.search(r"mov\s+r9d,0x([0-9a-f]+)", disassembly).group(1), 16)
key = f"MAINT-{first:04X}-{second:04X}"
response = subprocess.check_output([str(binary), "--unlock", key], text=True)
flag = re.search(r"GAIANSPACE\{[^}]+\}", response).group()
assert key == "MAINT-2189-8A44"
assert flag == "GAIANSPACE{m41nt_m0de_unl0cked}"
print(f"{key}: {flag}")
