# DDD characterization — Foundation One CO2 channel

Displacement damage dose adds a cumulative bias to every reading. The fit over the
qualification run is:

    drift(n) = round( 1.7 * n + 0.013 * n^2 )     [ppm], n = sample index

The reading on file is the as-flown value plus this drift. Subtract it to recover
the as-flown value. The logger also sits on a fixed CO2 baseline; the gas team keeps
quoting "about three-thirty ppm" and will not be pinned down further.

Lindqvist notes the thermistor on the same board also drifted, but that channel was
not recorded this run. Ignore it.
