#!/usr/bin/env python3
"""
805 - the-last-carrier

HALCYON-7's final QPSK frame, captured at 2 MHz with the carrier 37.5 kHz off
nominal. Nothing locks automatically; you derotate by hand.

Card (trust the rates):  fs = 2 MHz, Rs = 250 kHz, 8 samples/symbol, RRC a=0.35
Page (trust the shape): 4 phases, the usual neighbouring (Gray) map, MSB first,
                        "a wander in frequency and a fixed tilt in phase",
                        a bow word sent twice, then the letters.
Pell:                 "8 phases, trust me" / "same picture mode as the plate"  -> wrong

Steps
  1. RRC matched filter (alpha 0.35, 10-symbol span).
  2. Non-data-aided carrier recovery: raise the symbols to the 4th power so the
     four phases fold onto each other (Oduya's pencil) and search the residual
     frequency/timing for maximum 4th-power coherence J = |E{s^4}| / E{|s|^4}.
     -> CFO = +37 500 Hz, timing phase 7   (J = 0.994)
  3. A QPSK lock leaves a 4-fold ambiguity. Try all four rotations and keep the
     one whose opening bow is the real bow:
        CCSDS Attached Sync Marker with BCH = 0x1ACFFC1D, sent twice
        (Pell's television-satellite bow is in none of the other three.)
  4. Gray map, two bits per phase, MSB first.
"""
import numpy as np

SRC = "805/halcyon_iq.cs16"
FS, RS, SPS, ALPHA = 2_000_000.0, 250_000.0, 8, 0.35
GRAY = ["00", "01", "11", "10"]
CCSDS_ASM_BCH = 0x1ACFFC1D          # the bow

raw = np.fromfile(SRC, dtype="<i2")
x = raw[0::2] + 1j * raw[1::2]      # cs16 interleaved I,Q
N = len(x)
n = np.arange(N)


def rrc(alpha, nsym=10):
    M = nsym * SPS
    t = np.arange(-M // 2 + 1, M // 2 + 1) / SPS
    num = np.sin(np.pi * t * (1 - alpha)) + 4 * alpha * t * np.cos(np.pi * t * (1 + alpha))
    den = np.pi * t * (1 - (4 * alpha * t) ** 2)
    h = np.empty_like(num)
    ok = np.abs(den) > 1e-9
    h[ok], h[~ok] = num[ok] / den[ok], 0.0
    h[M // 2] = (1 - alpha) + 4 * alpha / np.pi     # removable singularity
    return h / h.sum()


H = np.fft.fft(rrc(ALPHA).astype(complex), N)


def match(x_derot):
    return np.fft.ifft(np.fft.fft(x_derot) * H)


def coherence(s):                  # 4th-power: folds the four phases together
    return abs(np.mean(s ** 4)) / np.mean(np.abs(s) ** 4)


# ---- 1/2: hand carrier lock: coarse then fine, CFO x timing ----
best = (0.0, 0.0, 0)
for f in np.arange(-140_000, 140_001, 25.0):
    y = match(x * np.exp(-2j * np.pi * f * n / FS))
    for t in range(SPS):
        j = coherence(y[t::SPS])
        if j > best[0]:
            best = (j, f, t)
best2 = (0.0, 0.0, 0)
for f in np.arange(best[1] - 30, best[1] + 30, 0.5):
    y = match(x * np.exp(-2j * np.pi * f * n / FS))
    for t in range(SPS):
        j = coherence(y[t::SPS])
        if j > best2[0]:
            best2 = (j, f, t)
J, CFO, T = best2
print(f"carrier lock: CFO = {CFO:+.1f} Hz ({CFO/FS:+.5f} fs), timing = {T}, J = {J:.4f}")

# ---- 3: the frame ----
y = match(x * np.exp(-2j * np.pi * CFO * n / FS))
s = y[T::SPS]
a = np.abs(s)
lo, hi = np.where(a > 0.5 * a.max())[0][[0, -1]]
core = s[lo:hi + 1]
print(f"frame: {len(core)} QPSK symbols  ({len(core)/2:.0f} bytes)")

# ---- 4: the four ways to hold the page ----
z0 = core * np.exp(-1j * np.angle(np.mean(core ** 4)) / 4)
for rot in range(4):
    q = np.round(np.angle(z0 * np.exp(-1j * rot * np.pi / 2)) / (np.pi / 2)) % 4
    bits = "".join(GRAY[int(v)] for v in q)
    by = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]
    bow = (by[0] << 24) | (by[1] << 16) | (by[2] << 8) | by[3]
    repeated = by[:4] == by[4:8]
    text = "".join(chr(b) if 32 <= b < 127 else "." for b in by[8:])
    tag = "  <== the bow" if bow == CCSDS_ASM_BCH and repeated else ""
    print(f"  rot {rot*90:3d}: bow 0x{bow:08X} x2={repeated}  letters {text!r}{tag}")

flag = None
for rot in range(4):
    q = np.round(np.angle(z0 * np.exp(-1j * rot * np.pi / 2)) / (np.pi / 2)) % 4
    bits = "".join(GRAY[int(v)] for v in q)
    by = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]
    bow = (by[0] << 24) | (by[1] << 16) | (by[2] << 8) | by[3]
    if bow == CCSDS_ASM_BCH and by[:4] == by[4:8]:
        text = "".join(chr(b) for b in by[8:])
        flag = text.split("FLAG:", 1)[1]
print("\nFLAG:", flag)