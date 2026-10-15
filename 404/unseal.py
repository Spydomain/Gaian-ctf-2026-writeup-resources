#!/usr/bin/env python3
"""Open a GaianSpace bench seal. Usage: python3 unseal.py <file.seal>"""
import hashlib, hmac, re, sys

MAGIC = b"SEAL1"


def norm(phrase):
    phrase = re.sub(r"[^\w\s]", " ", phrase.lower())
    return " ".join(phrase.split())


def keys(phrase, salt):
    key = hashlib.scrypt(norm(phrase).encode(), salt=salt, n=2**15, r=8, p=1,
                         maxmem=64 * 1024 * 1024, dklen=64)
    return key[:32], key[32:]


def stream(enc_key, length):
    out, counter = b"", 0
    while len(out) < length:
        out += hmac.new(enc_key, counter.to_bytes(4, "big"), hashlib.sha256).digest()
        counter += 1
    return out[:length]


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 unseal.py <file.seal>")
    blob = open(sys.argv[1], "rb").read()
    if not blob.startswith(MAGIC):
        sys.exit("That is not a bench seal.")
    salt, tag, ct = blob[5:21], blob[21:53], blob[53:]
    phrase = input("Phrase: ")
    enc_key, mac_key = keys(phrase, salt)
    if not hmac.compare_digest(hmac.new(mac_key, salt + ct, hashlib.sha256).digest(), tag):
        sys.exit("The seal stays shut.")
    print(bytes(a ^ b for a, b in zip(ct, stream(enc_key, len(ct)))).decode())


if __name__ == "__main__":
    main()
