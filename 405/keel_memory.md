# KEEL — burn table memory (ICD extract, rev F)

KEEL is SOLITAIRE's backup sequencer. It has no mind: it fires the rows of its burn table at their times, and that is all it does. The table lives in three radiation-tolerant banks, A, B and C. Each bank holds the whole table.

## Dump file (`keel_dump.bin`)

Little-endian throughout.

| Offset | Size | Field |
|---|---|---|
| 0 | 8 | magic `KEELDMP1` |
| 8 | 2 | format version (1) |
| 10 | 2 | table rows per bank |
| 12 | 2 | words per row (2) |
| 14 | 2 | banks (3, in the order A, B, C) |
| 16 | 2 | KEEL week at dump time |
| 18 | 4 | KEEL seconds of week at dump time |
| 22 | 10 | zero |
| 32 | … | bank A, then bank B, then bank C: rows × words slots of 8 bytes each |

Each 8-byte slot is one stored word: a 39-bit codeword in its low bits; the upper 25 bits are zero.

## EDAC: Hamming SEC-DED (39,32)

- Codeword positions are numbered 1 to 39. Slot bit *n* holds position *n* + 1.
- Positions 1, 2, 4, 8, 16 and 32 are check bits. Position 39 is the overall parity bit.
- The 32 data bits sit at the remaining positions 3, 5, 6, 7, 9, …, 38 in increasing order: data bit 0 at position 3, data bit 31 at position 38.
- Check bit *k* (at position *k*) makes the XOR of every position *p* ≤ 38 with *p* AND *k* ≠ 0 equal to zero.
- Position 39 makes the XOR of all 39 positions equal to zero.

On read, KEEL computes the syndrome (the XOR of the numbers of every position ≤ 38 that holds a 1) and the overall parity:

| Syndrome | Overall parity | KEEL's verdict |
|---|---|---|
| 0 | even | clean |
| ≠ 0 | odd | single error at the position the syndrome names; corrected |
| 0 | odd | single error in position 39; corrected |
| ≠ 0 | even | double error; uncorrectable |

## Table rows

Two words per row. Erased rows are all zero.

**Word 0, ignition time**

| Bits | Field |
|---|---|
| 31–22 | week: weeks since the KEEL epoch, modulo 1024 |
| 21–2 | seconds of week |
| 1–0 | zero |

**Word 1, the burn**

| Bits | Field |
|---|---|
| 31–16 | Δv in units of 0.1 m/s |
| 15–8 | burn id: `0x01` DEP, `0x11`–`0x1F` TCM-1 to TCM-15, `0x40` EOI (Earth orbit insertion, primary), `0x41` EOI-ALT (contingency capture one orbit later; fired only if EOI is missed) |
| 7–0 | thruster set |

## KEEL time

- KEEL epoch: SOLITAIRE's first boot, **2038-01-04 00:00:00 UTC** (a Monday). Week 0 starts there.
- KEEL time is UTC. No leap seconds have been added to UTC since KEEL was built, and none are modelled.

## Scrubbing

A scrubber reads every word of every bank once a week, corrects what EDAC can correct, and writes the corrected words back (WB). Its log is `scrub.log`.

## Handover readback

At handover the ground reads back the primary insertion burn, as KEEL will fly it: ignition in UTC as `YYYY-MM-DD HH:MM:SS` and Δv in m/s with one decimal. KEEL takes the ship when SOLITAIRE's handover phrase and that readback come together:

```
<handover phrase> <YYYY-MM-DD HH:MM:SS> <dv>
```
