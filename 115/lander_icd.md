# AO-111 lander — interface control, excerpt

AsterOre Inc. Lander bus and lander link. Excerpt for the assay desk; the full ICD is with flight software.

## Lander link housekeeping beacon

The lander OBC sends one housekeeping beacon about every six seconds while it is on the surface. All multi-byte fields are little-endian.

| Offset | Size | Field |
|-------:|-----:|-------|
| 0 | 2 | sync, ASCII `AO` |
| 2 | 1 | vehicle number (111) |
| 3 | 2 | frame counter |
| 5 | 4 | bus time, seconds since 2041-01-01T00:00:00Z |
| 9 | 1 | number of unit records that follow |
| 10 | 16 × n | unit records |

Unit record:

| Offset | Size | Field |
|-------:|-----:|-------|
| 0 | 1 | unit number |
| 1 | 1 | state |
| 2 | 2 | board temperature, signed, 0.01 °C |
| 4 | 4 | unit uptime, seconds |
| 8 | 8 | unit factory ID, 64-bit, as the unit reports it on the bus |

Units: 1 OBC, 2 hover camera relay, 3 XRF-9 assayer (Orlik), 4 anchor controller.
States: 0 off, 1 nominal, 2 safe, 3 vendor lock.

## Unit 3, XRF-9 assayer

The assayer is Orlik's reference design: an RP2350 controller board running Orlik's reference app, with an AsterOre build on top. It keeps its own results and logs on the controller flash. The lander OBC drives it over the bus console and can read the whole controller flash over the debug link, which is how the desk got `xrf9_flash.bin`.

Results leave the unit sealed. Orlik's results service unseals them for the customer.
