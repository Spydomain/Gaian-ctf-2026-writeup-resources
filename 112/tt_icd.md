# AO-111 — lander link time transfer (TT service)

AsterOre Inc. Excerpt from the AO-111 interface control document, rev C (2041-06-30).

## Purpose

The lander and the mothership keep separate clocks. The mothership runs on UTC. The lander OBC counts milliseconds since it last started (`obc_ms`, unsigned 32-bit). To place lander events in UTC, the mothership pings the lander over the lander link and the lander answers with its own clock readings.

## Exchange

1. The mothership sends a ping and records **T1**, its UTC at the **start of the ping transmission**.
2. The lander records **t2**, its `obc_ms` when the ping is **received** (the radio's RX-done interrupt, at the end of the packet).
3. The lander schedules its reply and records **t3**, its `obc_ms` at the **start of the reply transmission**. t2 and t3 go in the reply.
4. The mothership records **T4**, its UTC when the reply is **received** (RX done).

The mothership holds station about 500 m above the lander, so the light time (under 2 µs) can be ignored. Time on air cannot.

## Ping (mothership to lander), 5 bytes

| Offset | Size | Field |
|-------:|-----:|-------|
| 0 | 2 | ASCII `TQ` |
| 2 | 2 | sequence number |
| 4 | 1 | command: 0 = time ping, 1 = start anchor sequence (the lander answers, then keeps its radio quiet until the sequence is over) |

## Reply (lander to mothership), 14 bytes

| Offset | Size | Field |
|-------:|-----:|-------|
| 0 | 2 | ASCII `TT` |
| 2 | 1 | vehicle number (111) |
| 3 | 2 | sequence number of the ping being answered |
| 5 | 1 | command echoed |
| 6 | 4 | t2, `obc_ms` |
| 10 | 4 | t3, `obc_ms` |

All multi-byte fields are little-endian.

## Radio

Both directions use the same frequency, one at a time.

| | Uplink (ping) | Downlink (reply) |
|---|---|---|
| Frequency | 434.425 MHz | 434.425 MHz |
| Modulation | LoRa, BW 125 kHz | LoRa, BW 125 kHz |
| Spreading factor | SF7 | SF10 |
| Coding rate | 4/5 | 4/5 |
| Preamble | 8 symbols | 8 symbols |
| Header | explicit | explicit |
| Payload CRC | on | on |

Low data rate optimisation is switched on whenever the symbol time is longer than 16 ms, as the SX1276 datasheet requires. Time on air follows Semtech's formula for the SX1276 family (AN1200.13).

## Hover camera

During the anchor sequence the mothership's hover camera runs at 20 frames per second. Each frame is stamped with the mothership's UTC at the start of its exposure. The frame counter counts every frame taken; frames lost on the way down to the desk are missing from the index, not renumbered.
