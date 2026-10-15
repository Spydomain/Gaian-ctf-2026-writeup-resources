# Receiver bench notes — deep-space listening post

Downconverted baseband dumped straight to disk. Nothing fancy.

- File: `deep_space_capture.f32` — real-valued samples, **32-bit IEEE float, little-endian**, no header.
- Front-end gain was pinned; the trace looks like pure noise on the scope, as expected this far out.
- The keying is two-level, but the meaning is in the **changes**, not the levels — a change from one symbol to the next is one thing, holding steady is the other. Four samples per symbol.
- The transmitter cycles the same short burst over and over to survive the distance.
- Oscillator was steady for the whole capture — no drift correction was needed.

Lindqvist thinks it is just thermal noise and wants to close the file. He also keeps trying to read a single burst straight off and getting gibberish; he has not worked out that one burst is not enough and that the levels on their own say nothing. The night log mentions a stuck pixel at the band edge; ignore it, it is the display.
