# Ground radio notes — Kestrel LoRa listening watch

Parked the receiver on the CanSat band for the whole descent window.

- Band 868 MHz, SF9, link sync byte `0x12`. Payloads come off the modem still scrambled with that sync byte; the modem does not de-scramble for us.
- Two transmitters were in earshot. Our bird answers to node `0x1F`. The site weather beacon is node `0x2A` and never shuts up — it is not the CanSat.
- Frames do not always arrive in the order they were sent; each one carries its own sequence number, so order is recoverable.
- Lindqvist swears the longest, loudest node is the one that matters. The loudest node is the weather beacon.
