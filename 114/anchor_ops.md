# AO-111 lander — foot anchoring (ops procedure, excerpt)

## Hardware

Each of the three feet (A, B, C) carries a pyro-driven anchor screw. The sequencer fires them one at a time, about a minute apart, in the order it reports in the event log. A foot that bites holds the lander; a foot that doesn't lets that leg skid, and the lander pivots about the other two.

## Procedure

1. Sun fix: the OBC records the deck heading and loads the arm's target table for it.
2. Park the sun sensor (dust from the anchors).
3. Open a deck recorder session.
4. ARM, then FIRE each anchor in sequencer order, one at a time.
5. Close the recorder session. The summary carries the heading change across the sequence.
6. If the heading changed, rotate the arm's target table by the change before any placement.

Heading change is reported in whole degrees, clockwise as seen from above, positive.

## Pyro team notes

- A foot that bites gives a hard spike at the deck IMU, typically 10 g or more. A soft spike usually means the screw didn't bite.
- Each FIRE is visible in the power log as a bus dip of about 3 V.
- The deck settles within a couple of seconds of each shot.
