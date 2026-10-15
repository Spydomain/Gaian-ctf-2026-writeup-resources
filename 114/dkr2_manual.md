# DKR-2 deck recorder — operator's manual (rev C, firmware 1.3)

The DKR-2 is the lander's black box for the deck: a small microcontroller board with an LSM9DS1 9-axis IMU on its I2C bus, a bus power monitor, and a microSD card. Unit 2 on the lander bus.

## Sessions and files

The OBC opens a session before any deck event (hop, anchoring, arm moves) and closes it afterwards. During a session the recorder writes two files side by side on the card:

| File | Content |
|------|---------|
| `IMUnnnn.BIN` | IMU log, binary (below) |
| `PWRnnnn.CSV` | power monitor, 10 Hz, text: `ticks_ms,bus_v,bus_a,deck_c` |

`nnnn` is the session number. `CONFIG.TXT` is written by the OBC at session start.

The card is FAT16 with 2 KiB clusters. Both files grow at the same time, and the recorder takes the next free cluster for whichever file needs one.

At session close the recorder queues a summary (peak values, heading change, anchor table) for downlink. With `file_rotate=after_summary` the session's IMU file is deleted once the summary is queued; the power log stays.

## IMU settings

Taken from `CONFIG.TXT` at session start:

| Key | Default | Meaning |
|-----|---------|---------|
| `imu_odr_hz` | 476 | accelerometer and gyro output data rate |
| `imu_accel_fs_g` | 8 | accelerometer full scale, ±g |
| `imu_gyro_fs_dps` | 245 | gyro full scale, ±dps |
| `imu_fifo` | continuous | FIFO mode |

At the defaults one count is 0.244 mg (accelerometer) and 8.75 mdps (gyro).

The IMU sits flat on the deck plate. Its Z axis points up, out of the deck. The axes are right-handed.

## IMU log format (`IMUnnnn.BIN`)

The file starts with text lines (ASCII, `\n`): a title line, the I2C bus scan, a dump of the sensor's control registers (`REG <device> 0x<first address> <bytes from that address up>`, AG = accelerometer/gyro, M = magnetometer), and finally the line `START`.

After `START` the file is a stream of binary blocks, little-endian:

| Block | Layout |
|-------|--------|
| FIFO | `A5 46`, `uint32 ticks_ms`, `uint8 n`, then `n` FIFO slots of 12 bytes: gyro X, Y, Z, accel X, Y, Z as `int16` |
| Temperature | `A5 54`, `uint32 ticks_ms`, `int16` die temperature (16 counts per K, 0 = 25 °C), once a second |

`ticks_ms` is the recorder's own millisecond clock at the moment the FIFO was read, so every slot in a block carries the same tick; the slots are in the order the IMU sampled them, oldest first. The recorder clock is not the OBC clock.

## Notes

- After power-up the gyro needs a few seconds to settle. The recorder starts logging immediately anyway.
- The recorder never moves on its own. Anything in the IMU log is the deck.
