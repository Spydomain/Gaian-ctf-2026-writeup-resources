# Pilgrim-1 telemetry coding

Retyped from the 1977 handbook, section 4. The page was water-damaged. What could be read is below.

## Outer code

- Reed–Solomon (255, 223) over GF(2⁸). Field polynomial x⁸ + x⁴ + x³ + x² + 1. Generator roots α⁰ … α³¹. 223 data bytes first, 32 check bytes last.
- Interleave depth 4. In a frame, byte *i* of codeword *j* is sent at position 4*i* + *j*.

## Frame

- 32-bit sync marker `1ACFFC1D`, then 1020 coded bytes (4 × 255).
- After decoding, each frame's 892 data bytes are: frame counter (2 bytes, big-endian), number of valid bytes (2 bytes, big-endian), then the bytes. Filler after the valid bytes is `0x55`.
- Memory readouts are packed with the ground's usual deflate before they go out.

## Inner code

- Convolutional, constraint length 7, rate 1/2. Generators 171 and 133 (octal). Two symbols per bit, the 171 symbol first. The 133 symbol is inverted.
- The sync marker goes through the inner code with everything else.

## The recording

- `pilgrim_symbols.s8` is signed 8-bit samples, one per channel symbol, straight off the receiver. Positive means a 0 was sent.
- The recording does not start on a frame boundary.

## Desk

- Ade: "Take the sign of each sample, feed it to any decoder library. Viterbi is Viterbi."
- Ines: "We are 173 AU out. Every bit of every sample counts."
