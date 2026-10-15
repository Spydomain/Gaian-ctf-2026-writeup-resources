# FDS-16 — flight data subsystem, Pilgrim-1

Pages retyped from the 1977 handbook, with the load history the ground kept since.

## Machine

- 2048 words of 16 bits, addresses `000`–`7FF`. One accumulator **A**, one index register **X**, flags **Z** and **C**.
- Every instruction is one word: opcode in the top 5 bits, an 11-bit field in the rest (an address, or a small number).

| Op | Name | Does |
|----|------|------|
| 00 | HLT | stop |
| 01 | LDA a | A ← M[a] |
| 02 | STA a | M[a] ← A |
| 03 | ADD a | A ← A + M[a] (C = carry out) |
| 04 | SUB a | A ← A − M[a] (C = borrow) |
| 05 | AND a | A ← A & M[a] |
| 06 | XOR a | A ← A ^ M[a] |
| 07 | LDI n | A ← n |
| 08 | JMP a | go to a |
| 09 | JZ a | go to a if Z |
| 0A | JNZ a | go to a if not Z |
| 0B | JSR a | M[a] ← return address, then go to a + 1 |
| 0C | JMPI a | go to the address held in M[a] |
| 0D | LDX a | X ← M[a] |
| 0E | STX a | M[a] ← X |
| 0F | LDAX a | A ← M[a + X] (see below) |
| 10 | STAX a | M[a + X] ← A (see below) |
| 11 | INX | X ← X + 1 |
| 12 | DEX | X ← X − 1, Z from X |
| 13 | OUT | A goes into the telemetry frame |
| 14 | SHL n | shift A left n |
| 15 | SHR n | shift A right n |
| 16 | ROL n | rotate A left n |
| 17 | TAX | X ← A |
| 18 | TXA | A ← X |
| 19 | ADDI n | A ← A + n |
| 1A | JC a | go to a if C |
| 1B | LDXI n | X ← n |

Z follows A after every instruction that changes A. A subroutine is entered with `JSR`; its first word holds the return address, and it returns with `JMPI` on that word.

**Indexed addressing.** To save gates, the index adder is five bits wide. `a + X` is computed only in the low five bits of the address; the carry is dropped. A table read with `LDAX` must not cross a 32-word page, or it wraps to the start of the page.

## Memory map (1977)

| Range | Use |
|-------|-----|
| `000`–`0FF` | Executive, housekeeping, shared variables |
| `100`–`5FF` | Attitude, command, science formatting |
| `600`–`6FF` | Telemetry signature module and test code |
| `700`–`7FF` | Spare routines and calibration |

Free in the 1977 load: `2E0`–`2FF`, `3A0`–`3DF`, `4F0`–`4FF`, `5D0`–`5EF`, `770`–`78F`.

## Load history (ground records)

- 1977 — launch load. The signature module's table sits at `2E0`, per page 7-3.
- 1981 — science formatting outgrew bank 1. The signature module was moved to `600` in a hurry. The signature has printed nonsense in every frame since. Nobody had time to find out why.
- 1998 — thermal correction routine added to the housekeeping cycle. The record of where it was loaded is missing.
- 2026 — bank 3 lower (`600`–`6FF`) no longer holds data. Reads come back as noise.

## Uplink

- One patch, one pass. The window holds **96 words**. A patch is a list of `ADDR WORD` writes, in hex.
- `fds_sim.py` is the ground's bench model. By default it behaves like the spacecraft does now. `--no-fault` behaves like the healthy 1977 machine.

## Desk

- Ade: "Copy bank 3 into the big free block at `3A0`, fix the call, send it. Sixty-four words, plenty of room."
- Ines: "That map is older than you are."
