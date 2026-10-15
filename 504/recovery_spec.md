# Power-management block — dump layout and key scheme

`reg_dump.bin` is, in order:

| Offset | Size | Field |
|--------|------|-------|
| 0x00   | 32   | R0..R7, eight 32-bit registers, little-endian |
| 0x20   | 4    | integrity word: CRC-32 (zlib/ISO, little-endian) of the 32 healthy register bytes |
| 0x24   | ...  | sealed payload: AES-ECB ciphertext of the mission flag (PKCS#7) |

Key scheme (flight build): `key = SHA-256(R0..R7 bytes)[:16]`.

A healthy block satisfies the integrity word. The latch-up set exactly one register
bit high, so the stored CRC no longer matches. The reserved high nibble of R7 is a
favourite target for scrubbing routines, but that is not where this event landed.
