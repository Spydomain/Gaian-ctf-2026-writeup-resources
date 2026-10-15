#!/usr/bin/env python3
"""Foundation One CanSat - flight firmware emulator (ground test harness).
Speaks the LoRa command link over TCP. Commands are newline-terminated:

    PING                 -> PONG
    TLM                  -> current telemetry frame
    CFG <hexbytes>       -> load config block into the config register
    CAL <hexbytes>       -> load calibration vector (bounded)
    DIAG                 -> maintenance diagnostic register readout
    AUTH <hex4>          -> enter maintenance if the 4-byte service key matches
    DUMP                 -> maintenance only: dump the service telemetry page
    HELP                 -> this list

Flight build. Do not ship the ground harness."""
import socket, threading, os, binascii, zlib

_TLM_FRAME = (b"TLM alt=312m vbat=4.01V temp=19.4C co2=712ppm "
              b"ax=0.01 ay=-0.02 az=0.98 state=DESCENT svc=0xDEADBEEF")

# service page image, as burned (whitened)
_SVC_PAGE = bytes.fromhex(
    "d4790420d75ab804457d0be0e9c061f6e17995a0705d55d74d0edb8a1f7c764ae0fd77f3b322c07350"
    "83c146f3e6fe6b2c30ba46898d4dd4768b8e3f1527f47235f30bc2edeed7eaa146f78c6913f572201b")

def _whiten(data, seed):
    s = seed or 0xACE1
    out = bytearray()
    for c in data:
        b = 0
        for _ in range(8):
            bit = ((s >> 0) ^ (s >> 2) ^ (s >> 3) ^ (s >> 5)) & 1
            s = (s >> 1) | (bit << 15)
            b = (b << 1) | bit
        out.append(c ^ b)
    return bytes(out)

class Sat:
    def __init__(self):
        # 24-byte scratch register.
        self.mem = bytearray(24)
        self.mem[16:20] = os.urandom(4)      # service key, set at boot, never printed
        self.calreg = bytearray(8)
        self.maint = False

    def cfg(self, payload):
        n = len(payload)
        for i in range(n):
            self.mem[i] = payload[i]
        return b"CFG LOADED %d bytes" % n

    def cal(self, payload):
        if len(payload) > 8:
            return b"CAL REJECT (vector too long, max 8)"
        self.calreg[:len(payload)] = payload
        return b"CAL OK %d bytes" % len(payload)

    def diag(self):
        # scrambled diagnostic register image (not the service key)
        img = bytes((b ^ 0x5A) for b in self.calreg) or b"\x00" * 8
        return b"DIAG reg=" + binascii.hexlify(img).upper()

    def auth(self, key4):
        if len(key4) == 4 and bytes(key4) == bytes(self.mem[16:20]):
            self.maint = True
            return b"MAINT OK"
        return b"DENIED"

    def dump(self):
        if not self.maint:
            return b"LOCKED (maintenance required)"
        return _whiten(_SVC_PAGE, zlib.crc32(self.tlm()) & 0xFFFF)

    def tlm(self):
        return _TLM_FRAME

def handle(conn, addr):
    sat = Sat()
    conn.sendall(b"Foundation One CanSat link up. HELP for commands.\r\n")
    f = conn.makefile("rb")
    while True:
        line = f.readline()
        if not line: break
        parts = line.split()
        if not parts: continue
        op = parts[0].upper()
        try:
            if op == b"PING": conn.sendall(b"PONG\r\n")
            elif op == b"TLM": conn.sendall(sat.tlm()+b"\r\n")
            elif op == b"HELP": conn.sendall(b"PING TLM CFG CAL DIAG AUTH DUMP HELP\r\n")
            elif op == b"CFG" and len(parts) >= 2:
                conn.sendall(sat.cfg(binascii.unhexlify(parts[1]))+b"\r\n")
            elif op == b"CAL" and len(parts) >= 2:
                conn.sendall(sat.cal(binascii.unhexlify(parts[1]))+b"\r\n")
            elif op == b"DIAG": conn.sendall(sat.diag()+b"\r\n")
            elif op == b"AUTH" and len(parts) >= 2:
                conn.sendall(sat.auth(binascii.unhexlify(parts[1]))+b"\r\n")
            elif op == b"DUMP": conn.sendall(sat.dump()+b"\r\n")
            else: conn.sendall(b"ERR unknown or malformed\r\n")
        except Exception:
            conn.sendall(b"ERR bad frame\r\n")
    conn.close()

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 9707)); s.listen(16)
    print("Foundation One CanSat link on 0.0.0.0:9707")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
