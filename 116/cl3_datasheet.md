# CL-3 cell logger — datasheet (extract)

A small logger that rides inside a sealed sample cell. One BME688 (pressure, temperature, humidity) and one SCD-41 (CO2) on the same I2C bus, a microcontroller, a radio for status bursts and a coin cell.

## Environment record (`*_env.csv`)

| Column | Meaning |
|-|-|
| `rec` | record counter, +1 per environment record, from 0 at power-up |
| `ms` | milliseconds since power-up |
| `t_adc` | BME688 temperature ADC, 20 bit, as read |
| `p_adc` | BME688 pressure ADC, 20 bit, as read |
| `h_adc` | BME688 humidity ADC, 16 bit, as read |

The BME688 runs in forced mode once a second: temperature and pressure oversampling x16, humidity x2, IIR filter off, gas heater off. The logger stores the ADC words only; convert them with the Bosch BME68x compensation formulas. Every BME688 carries its own calibration in its NVM (registers 0x8A–0xA0, 0xE1–0xEE and 0x00–0x02).

## CO2 record (`*_co2.csv`)

The SCD-41 measures every 5 s. `rec` is the environment counter at the moment of the read. `co2_ppm` as reported; temperature = -45 + 175 x `t_raw` / 65535 degC; RH = 100 x `rh_raw` / 65535 %. The SCD-41 is not specified below 400 ppm.

## Power and radio

The logger keys its radio for a status burst of about 25 s every ten minutes.

## Factory calibration record

Decoded BME688 parameters recorded at final test, logger S/N CL3-0417:

| Parameter | Value |
|-|-|
| `T1` | 25774 |
| `T2` | 26791 |
| `T3` | 3 |
| `P1` | 36882 |
| `P2` | -10514 |
| `P3` | 88 |
| `P4` | 7912 |
| `P5` | -142 |
| `P6` | 30 |
| `P7` | 37 |
| `P8` | -2187 |
| `P9` | -3076 |
| `P10` | 30 |
| `H1` | 784 |
| `H2` | 1029 |
| `H3` | 0 |
| `H4` | 45 |
| `H5` | 20 |
| `H6` | 120 |
| `H7` | -100 |
