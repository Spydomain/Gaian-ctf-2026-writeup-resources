# Pilgrim-1 memory readout — desk notes, 2026-10-14

## What was asked

- 2026-10-11: the 704 patch went up (`uplink_2026-10-11.txt`, exactly as sent). One pass, accepted.
- 2026-10-13: the signature came back clean in every frame. Champagne, briefly.
- 2026-10-13: Ines asked for five full memory readouts, three on the first pass and two on the second, "before anyone touches that machine again".
- 2026-10-14: all five readouts arrived. `readout_frames.log` is the station's frame log, every frame as received, including the ones it did not like.

## Readout frame (FDS-16 memory dump format, handbook page 9-2)

| Bytes | Field |
|------:|-------|
| 2 | sync, ASCII `P1` |
| 1 | readout number, 1–5 |
| 1 | frame number in the readout, from 0 |
| 2 | first address in the frame, big-endian |
| 2 × n | the memory words, big-endian, consecutive addresses (80 per frame, 48 in the last) |
| 2 | checksum: the 16-bit sum of the words |

Everything after the first six bytes (the words and the checksum) is scrambled before it leaves the spacecraft, so that long runs of equal words still give the receiver bit transitions. The scrambler is a 16-bit Galois LFSR, shifted right, feedback mask `B400` when the bit shifted out is 1. Each output byte is eight shifts, the first bit out is the byte's least significant bit. The register is loaded with `(readout << 8 | frame) XOR 5A5A` at the start of each frame; the scrambled byte is the data byte XOR the LFSR byte.

The FDS reads its memory while it runs. A readout is what the memory held at the moment each word was read.

## Station

The receiver loses symbol timing towards the end of long frames on this link. The checksum fails on about half the frames. It has always failed that often; that is why we ask for more than one readout.

## Desk

- Ade: "Diff it against the golden image plus the patch. Every word that doesn't match is a dead cell. Five minutes."
- Ines: "Bank 3 lower we already know about. I want to know if anything else is going."
