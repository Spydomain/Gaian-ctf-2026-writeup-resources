#!/usr/bin/env python3
"""FDS-16 bench simulator. Pilgrim-1 flight data subsystem, ground model.

usage:  python3 fds_sim.py fds_golden.img [patch.txt] [--no-fault] [--trace N]

The image is 2048 big-endian 16-bit words. A patch is text, one write per line:
    ADDR WORD        (hex, e.g.  2E0 1A2B)   '#' starts a comment.
A patch longer than the uplink window is refused. By default the simulator
models the spacecraft as it is now: memory 0x600-0x6FF does not hold data.
"""
import sys

MEM = 0x800
DEAD = range(0x600, 0x700)
UPLINK_WORDS = 96
STEP_LIMIT = 200_000

OPS = ['HLT', 'LDA', 'STA', 'ADD', 'SUB', 'AND', 'XOR', 'LDI', 'JMP', 'JZ', 'JNZ', 'JSR', 'JMPI',
       'LDX', 'STX', 'LDAX', 'STAX', 'INX', 'DEX', 'OUT', 'SHL', 'SHR', 'ROL', 'TAX', 'TXA',
       'ADDI', 'JC', 'LDXI']


class FDS:
    def __init__(self, words, fault=True):
        self.m = list(words); self.fault = fault
        self.a = self.x = self.pc = 0; self.z = self.c = 0
        self.out = []; self.noise = 0xACE1

    def _noise(self):
        n = self.noise
        n ^= (n << 7) & 0xFFFF; n ^= n >> 9; n ^= (n << 8) & 0xFFFF
        self.noise = n
        return n

    def rd(self, addr):
        addr &= 0x7FF
        if self.fault and addr in DEAD:
            return self._noise()
        return self.m[addr]

    def wr(self, addr, val):
        addr &= 0x7FF
        if self.fault and addr in DEAD:
            return
        self.m[addr] = val & 0xFFFF

    def setz(self, v):
        self.z = int((v & 0xFFFF) == 0)

    def step(self):
        w = self.rd(self.pc); op, a = w >> 11, w & 0x7FF
        self.pc = (self.pc + 1) & 0x7FF
        if op >= len(OPS):
            return False                                   # illegal instruction: the FDS halts
        name = OPS[op]
        if name == 'HLT': return False
        elif name == 'LDA': self.a = self.rd(a); self.setz(self.a)
        elif name == 'STA': self.wr(a, self.a)
        elif name == 'ADD':
            r = self.a + self.rd(a); self.c = r >> 16; self.a = r & 0xFFFF; self.setz(self.a)
        elif name == 'SUB':
            r = self.a - self.rd(a); self.c = int(r < 0); self.a = r & 0xFFFF; self.setz(self.a)
        elif name == 'AND': self.a &= self.rd(a); self.setz(self.a)
        elif name == 'XOR': self.a ^= self.rd(a); self.setz(self.a)
        elif name == 'LDI': self.a = a; self.setz(self.a)
        elif name == 'JMP': self.pc = a
        elif name == 'JZ':
            if self.z: self.pc = a
        elif name == 'JNZ':
            if not self.z: self.pc = a
        elif name == 'JSR': self.wr(a, self.pc); self.pc = (a + 1) & 0x7FF
        elif name == 'JMPI': self.pc = self.rd(a) & 0x7FF
        elif name == 'LDX': self.x = self.rd(a)
        elif name == 'STX': self.wr(a, self.x)
        elif name in ('LDAX', 'STAX'):
            # the index adder is five bits wide: the carry never leaves the 32-word page
            ea = (a & 0x7E0) | ((a + self.x) & 0x1F)
            if name == 'LDAX': self.a = self.rd(ea); self.setz(self.a)
            else: self.wr(ea, self.a)
        elif name == 'INX': self.x = (self.x + 1) & 0xFFFF
        elif name == 'DEX': self.x = (self.x - 1) & 0xFFFF; self.setz(self.x)
        elif name == 'OUT': self.out.append(self.a)
        elif name == 'SHL':
            n = a & 0xF; self.c = (self.a >> (16 - n)) & 1 if n else 0; self.a = (self.a << n) & 0xFFFF; self.setz(self.a)
        elif name == 'SHR':
            n = a & 0xF; self.c = (self.a >> (n - 1)) & 1 if n else 0; self.a >>= n; self.setz(self.a)
        elif name == 'ROL':
            n = a & 0xF; self.a = ((self.a << n) | (self.a >> (16 - n))) & 0xFFFF; self.setz(self.a)
        elif name == 'TAX': self.x = self.a
        elif name == 'TXA': self.a = self.x; self.setz(self.a)
        elif name == 'ADDI':
            r = self.a + a; self.c = r >> 16; self.a = r & 0xFFFF; self.setz(self.a)
        elif name == 'JC':
            if self.c: self.pc = a
        elif name == 'LDXI': self.x = a
        return True


def load_image(path):
    b = open(path, 'rb').read()
    assert len(b) == 2 * MEM, 'image must be 2048 words'
    return [int.from_bytes(b[i:i + 2], 'big') for i in range(0, len(b), 2)]


def load_patch(path):
    writes = []
    for line in open(path):
        line = line.split('#')[0].strip()
        if not line: continue
        ad, wd = line.replace(':', ' ').split()[:2]
        writes.append((int(ad, 16), int(wd, 16)))
    return writes


def show(words):
    for i in range(0, len(words), 8):
        row = words[i:i + 8]
        txt = ''.join(chr(c) if 32 <= c < 127 else '.' for w in row for c in (w >> 8, w & 0xFF))
        print('  ' + ' '.join(f'{w:04X}' for w in row).ljust(40) + ' ' + txt)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    fault = '--no-fault' not in sys.argv
    trace = 0
    if '--trace' in sys.argv: trace = int(sys.argv[sys.argv.index('--trace') + 1]); args = [a for a in args if a != str(trace)]
    if not args: print(__doc__); return
    words = load_image(args[0])
    if len(args) > 1:
        patch = load_patch(args[1])
        if len(patch) > UPLINK_WORDS:
            print(f'uplink refused: {len(patch)} words, the window holds {UPLINK_WORDS}'); return
        for ad, wd in patch:
            if ad >= MEM: print(f'uplink refused: address {ad:X}'); return
            if fault and ad in DEAD: print(f'warning: write to {ad:03X} will not stick')
            words[ad] = wd & 0xFFFF
        print(f'uplink accepted: {len(patch)} words')
    fds = FDS(words, fault)
    steps = 0
    while steps < STEP_LIMIT:
        if trace and steps < trace:
            print(f'{fds.pc:03X}: {fds.rd(fds.pc) if not (fault and fds.pc in DEAD) else 0:04X}  A={fds.a:04X} X={fds.x:04X}')
        if not fds.step(): break
        steps += 1
    print(f'FDS stopped after {steps} steps at {fds.pc:03X}' + (' (step limit)' if steps >= STEP_LIMIT else ''))
    print(f'telemetry ({len(fds.out)} words):')
    show(fds.out[:400])


if __name__ == '__main__':
    main()
