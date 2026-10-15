# AO-111 descent card — 2041 QM23

Flight dynamics, AsterOre Inc. Signed off for a single release. There is no second lander.

## The rock

- Elongated. It spins about its shortest axis.
- GM = 0.2123 m³/s². For the descent, treat it as a point mass.
- The metal patch is on one of the two broad faces of the body. The radar team says it is brighter than the regolith around it. They did not say which face, and they have stopped answering email.

## The hover station

- AO-111 holds station 500 m from the centre of the rock, in the rock's equatorial plane, on the Sun line. The hover camera looks straight down the descent axis. That is where `hover_photometry.csv` came from.
- Hover station clock is UTC. The camera did not run during the gaps; it was busy talking to Earth or cooling down.

## The lander

- Released from the hover station straight down the descent axis by a spring. Then nothing: no thrusters, no corrections, no radio from Earth.
- Spring A: 0.020 m/s. Spring B: 0.080 m/s. The spring is chosen on the order and cannot be changed after release.
- Contact happens 50.0 m from the centre of the rock. The legs are rated to 0.110 m/s at contact. Faster than that and the lander bounces back into space.
- The anchor must touch within 2.5° of the centre of the metal patch. At contact, the patch has to be facing straight back up the descent axis.

## Release slots

- The valve opens only on a slot. Slot `0000` is 2041-11-04 16:00:00 UTC. One slot every 10 s, up to slot `0539`. Release happens at the start of the slot.
- Outside that window the hover station is in the rock's shadow or out of contact.

## Desk

- Kaito: "Periodogram, tallest peak, that's the period. Then release when the patch is under us."
- Sunniva: "It's under us when it lands, not when it leaves."
