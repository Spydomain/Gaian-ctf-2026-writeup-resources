# Descent integration — DR-ONE powered descent

Inertial frame, metres, z is up. Integrate the recovered thrust plan forward from
the release state under local gravity until the vehicle reaches the ground (z <= 0).

Release state:

    position (x, y, z) = (2000.0, -500.0, 1500.0)   m
    velocity (vx,vy,vz) = (-40.0,  10.0,  -60.0)    m/s

Constants:

    local surface gravity g = 3.711 m/s^2   (acts in -z)
    time step dt = 0.1 s   (the profile is sampled at dt)

Method (use exactly this so the site is reproducible):

    for each row (thr_ax, thr_ay, thr_az):
        a = (thr_ax, thr_ay, thr_az + (-g))     # total acceleration
        v = v + a*dt                            # update velocity first
        p = p + v*dt                            # then position
        stop when p.z <= 0  -> (p.x, p.y) is the landing site

Report x and y rounded to the nearest 10 m. The barometric channel on the aircraft
read nonsense this far out; ignore it, the plan is purely inertial.
