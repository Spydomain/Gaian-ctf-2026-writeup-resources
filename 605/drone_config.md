# DR-ONE configuration page (fw 2.0.7) — applies to DR-ONE and DR-ONE-Q

## Airframe

Coaxial rotorcraft: two counter-rotating rotors on one mast. Roll and pitch come from the lower swashplate, which three servos tilt. Servo positions around the mast, in degrees clockwise from the nose, seen from above:

| Servo | Position |
|-------|----------|
| S1 | 90 (right) |
| S2 | 210 (rear left) |
| S3 | 330 (front left) |

A servo that loses power lets its point of the swashplate drop, and the airframe tips down on that servo's side faster than the other two can catch it.

## IMU (LSM9DS1, on the flight controller board, I2C)

| Setting | Value |
|---------|-------|
| Mounting | flat on the FC tray; IMU +X toward the nose, IMU +Y to the left, IMU +Z up |
| Output data rate | 476 Hz, FIFO continuous |
| Accelerometer full scale | ±16 g |
| Gyro full scale | ±245 dps (chosen for resolution in hover; the attitude loop never needs more) |

## Black box (BBX)

- microSD, FAT16, one file per flight: `BBXnnnn.BIN`. The black box is powered with the flight controller, so its `ticks_ms` count from that flight's power-up.
- The file is written as it goes; the directory entry and the FAT are brought up to date every few seconds.
- The file starts with a short text header (title, I2C bus scan, a dump of the IMU's control registers, `START`), then binary blocks in the BBX 2.0 format, one per FIFO read, each stamped with `ticks_ms`.
