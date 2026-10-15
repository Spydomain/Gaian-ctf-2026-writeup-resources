#!/usr/bin/env python3
"""
604 - ice-vault

No word, no list, no hint: the passphrase is five lowercase letters and has to
be ground out of the full 26^5 space (11,881,376 candidates).

There is no wordlist shortcut here, so the only thing that matters is making the
grind fast and, more importantly, making the *verifier* correct.

--- 1. getting a hash out of the archive -------------------------------------
`7z2john` is the usual tool, but the box has no Compress::Raw::Lzma, and more
importantly this archive's kEncodedHeader carries no kCRC record, so 7z2john
walks away with an empty hash.  So build the hash directly:

  * kEncodedHeader @ 464, PackPos = 304 -> the packed stream sits at
    file offset 32 + PackPos = 336, 128 bytes
  * AES-256/SHA-256 coder, properties 53 0f <16-byte iv>
      cycles power = 0x53 & 0x3f = 19   -> 2^19 = 524288 SHA-256 rounds
      salt length  = 0, iv length = 16
  * unpack_size = 123  -> padded with 5 bytes of 0x05

--- 2. choosing the verifier ----------------------------------------------
The obvious check ("CRC32 of the decrypted header == NextHeaderCRC") is wrong
here, and wrong in a way that costs you the whole run:

  * hashcat -m 11600 only accepts that style, but it refuses data-type 128, and
  * NextHeaderCRC is not usable: 7-Zip (and this archive) store the CRC of the
    *stored* header, not of the decrypted one.  Confirmed on a control archive:
    the declared NextHeaderCRC equals crc32() of the on-disk kEncodedHeader,
    while the CRC a cracker needs lives in a kCRC record inside the encrypted
    header - which this vault does not have.
  * Setting unpack_len == data_len makes the padding check vacuous and john
    "cracks" the very first candidate (aaaaa), which 7z rejects.  That is a
    silent false positive, not a solution.

So: type 128 (truncated) + unpack_len 123 vs data_len 128 -> padding size 5, and
verification is pure PKCS#7 padding.  No stored CRC required, and 5 bytes of 0x05
is a 2^-40 filter, so false positives are not a practical concern.

--- 3. the grind ------------------------------------------------------------
john's 7z-opencl backend runs on the GPU: ~7100 candidates/s -> the full
26^5 space in roughly 35-40 minutes.
"""
import os
import re
import struct
import subprocess
import sys

from pathlib import Path
ROOT = Path(__file__).resolve().parent
VAULT = str(ROOT / "mission_vault.7z")
WORK = str(ROOT / "crack-work")
SIG = b"7z\xbc\xaf\x27\x1c"
AES = bytes.fromhex("06f10701")


def num(b, p):
    first = b[p]; p += 1
    mask, v = 0x80, 0
    for i in range(8):
        if not (first & mask):
            return v | ((first & (mask - 1)) << (8 * i)), p
        v |= b[p] << (8 * i); p += 1; mask >>= 1
    return v, p


def extract(path):
    d = open(path, "rb").read()
    assert d[:6] == SIG
    at = [i for i in range(32, len(d) - 1) if d[i] == 0x17 and d[i + 1] == 0x06][-1]
    i = at + 2                                    # kPackInfo (0x06) already consumed
    pack_pos, i = num(d, i)
    npack, i = num(d, i)
    assert d[i] == 0x09; i += 1                   # kSize marker
    sizes = []
    for _ in range(npack):
        s, i = num(d, i); sizes.append(s)
    assert d[i] == 0x00 and d[i + 1] == 0x07; i += 2   # kEnd, kUnpackInfo
    assert d[i] == 0x0B; i += 1                   # kFolder
    nfolders, i = num(d, i); i += 1               # external flag
    ncoders, i = num(d, i)
    main = d[i]; i += 1
    ids = main & 0x0F
    assert d[i:i + ids] == AES; i += ids
    psize, i = num(d, i)
    attrs = d[i:i + psize]; i += psize
    assert d[i] == 0x0C; i += 1                   # kCodersUnpackSize
    unpack, i = num(d, i)

    cycles = attrs[0] & 0x3F
    salt_len = ((attrs[0] >> 7) & 1) + (attrs[1] >> 4)
    iv_len = ((attrs[0] >> 6) & 1) + (attrs[1] & 0x0F)
    o = 2 + salt_len
    salt = attrs[2:o]
    iv = (attrs[o:o + iv_len] + b"\x00" * 16)[:16]

    ct = d[32 + pack_pos: 32 + pack_pos + sizes[0]]
    pad = len(ct) - unpack
    assert pad in range(1, 16)
    print(f"[+] kEncodedHeader @{at}  ciphertext @ {32+pack_pos} ({len(ct)} B)")
    print(f"[+] AES-256/SHA-256  2^{cycles} = {1<<cycles} SHA-256 rounds  "
          f"salt[{salt_len}]  iv={iv.hex()}")
    print(f"[+] unpack_size={unpack}  -> PKCS#7 padding = {pad} bytes")
    return f"{os.path.basename(path)}:$7z$128${cycles}${salt_len}${salt.hex()}" \
           f"${iv_len}${iv.hex()}$0${len(ct)}${unpack}${ct.hex()}"


if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    os.chdir(WORK)
    h = extract(VAULT)
    open("vault_j2.hash", "w").write(h + "\n")
    print(f"[+] wrote {WORK}/vault_j2.hash")
    print("[+] john --format=7z-opencl --mask='?l?l?l?l?l' vault_j2.hash")
    if "--run" in sys.argv:
        subprocess.run(["john", "--format=7z-opencl", "--mask=?l?l?l?l?l",
                        "--session=vault2", "vault_j2.hash"])
