#!/usr/bin/env python3
"""Emergency-safe PCA9685 shutdown: set every channel to zero."""

import busio
from board import SCL, SDA
from adafruit_pca9685 import PCA9685


def main():
    i2c = busio.I2C(SCL, SDA)
    pca = PCA9685(i2c)
    try:
        # This older driver enables PCA9685 register auto-increment only when
        # frequency is configured. StructArray channel writes require it.
        pca.frequency = 100
        # Index explicitly: older adafruit_pca9685 releases do not reliably
        # iterate PCAChannels and may repeatedly address channel 0.
        for channel in range(16):
            pca.channels[channel].duty_cycle = 0
    finally:
        pca.deinit()
    print("All 16 PCA9685 channels are OFF.")


if __name__ == "__main__":
    main()
