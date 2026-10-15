# PA case thermal model — Foundation One radio

First-order lumped model, one sample per second:

    T[n+1] = T[n] + dt * ( K * P[n] - (T[n] - Tamb) / tau )

    dt   = 1.0 s
    K    = heating per unit of drive count, per step      (bench fit: sheet missing)
    tau  = thermal time constant, s                       (bench fit: sheet missing)
    Tamb = ambient / sink temperature, C                  (bench fit: sheet missing)

The bench-fit sheet left with the previous thermal lead. Lindqvist says the numbers
do not need the sheet: the model is linear in all three, and the team has always
re-fitted them from any stretch where the drive is already known.

`P[n]` is the amplifier drive count for step n — the quantity that was never logged.

The sun sensor on the same bracket also warmed during the pass; that channel is not
in this log and is not part of the model.
