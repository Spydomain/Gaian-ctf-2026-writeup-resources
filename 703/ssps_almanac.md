# Solar System Positioning Service — user almanac (excerpt)

Issue 2026-10. For receivers beyond the planets.

## Beacons

Eight beacons, two per outer planet, at that planet's L4 and L5 points: `JUP-L4`, `JUP-L5`, `SAT-L4`, `SAT-L5`, `URA-L4`, `URA-L5`, `NEP-L4`, `NEP-L5`.

The service defines a beacon's position exactly, at the instant it transmits:

- Take the heliocentric position **r** and velocity **v** of the planet's **system barycentre**, from JPL DE440, in the ICRF (J2000) frame.
- The planet's orbit normal is **h** = **r** × **v**.
- L4 is **r** rotated by +60° about **h**. L5 is **r** rotated by −60° about **h**. Same distance from the Sun as the planet.
- Add the Sun's position to get the beacon's position relative to the solar-system barycentre.

## Signal

- Each pulse carries the time it left the beacon (`tx_stamp_tdb_s`): TDB seconds past J2000, from the beacon's own clock, which the service keeps steered to TDB.
- A receiver logs, at one instant of its own clock, the stamp of the pulse arriving from each beacon at that instant.
- Pulses travel in straight lines at c = 299 792.458 km/s. The service ignores everything smaller than a microsecond.

## Operations bulletins

- `NEP-L4` — power margin low, C/N0 reduced about 3 dB. Timing unaffected.
- `URA-L5` — antenna repointed 2026-09-28. Timing unaffected.
- `SAT-L5` — time transfer to the beacon missed two windows. Clock steering pending.
- `JUP-L4` — nominal.

## Pilgrim-1 note (GaianSpace desk)

The SSPS receiver on Pilgrim-1 was added in a 1980s software load and has never had its clock set since the 2019 fault. It counts seconds past J2000, but nobody knows from where. `ssps_receiver_log.csv` is three snapshots it took on 2026-10-09 and sent home.

- Ade: "Easy. Take where the beacons are now and solve."
- Ines: "Now is not when they spoke."
