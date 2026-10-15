# Pilgrim-1 desk notes

GaianSpace deep-space desk. Pilgrim-1 left Earth in 1977. It is about one light-day out now.

- At 18:54:50.1 UTC the station saw the carrier jump. That is what the spacecraft does when it drops into safe mode and swaps to the backup oscillator. Everything after that has been garbage.
- The frame log (`frame_log.csv`) is every frame we received around then, stamped with the **spacecraft clock**, not with when we got it. One frame every 48 s of spacecraft clock.
- The data computer writes a status word into every frame. The word in the frame being sent at the moment it switched is the one engineering wants. It tells them which routine was running.
- The SPICE kernels are in `kernels.zip`. Load `pilgrim.tm`. Pilgrim-1 is NAIF ID -901, and so is its clock.
- The clock was reset after the 2019 fault. The ground has been fitting its drift ever since.

Overheard:

- Ade (nights): "The step was at 18:54:50. Find the frame stamped 18:54:50, done."
- Ines: "Stamped by what?"
- Ade: "Fine. The clock ticks once a second, it was reset in March 2019, count forward from there."
