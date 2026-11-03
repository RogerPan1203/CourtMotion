#!/usr/bin/env python3
"""
Configurable synchronized motor sweep on PCA9685 channels 2 and 4.

Both outputs are driven together. Defaults are channel 2 at 30% and channel 4
at 30%, with independently validated command-line settings.

Channel 2: 0 → 30% over 3s, then 30% → 0 over 3s
Channel 4: 0 → 30% over 3s, then 30% → 0 over 3s
Then repeat.

Ctrl+C to stop (both channels off on exit).
"""

import argparse
import time
import busio
from board import SCL, SDA
from adafruit_pca9685 import PCA9685

CHANNELS = (2, 4)
STEP_S = 0.10


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ch2-pct", type=float, default=30.0)
    parser.add_argument("--ch4-pct", type=float, default=30.0)
    parser.add_argument("--duration", type=float, default=3.0)
    args = parser.parse_args()
    if not 0 <= args.ch2_pct <= 30:
        parser.error("channel 2 must be between 0 and 30 percent")
    if not 0 <= args.ch4_pct <= 30:
        parser.error("channel 4 must be between 0 and 30 percent")
    if not 1 <= args.duration <= 10:
        parser.error("duration must be between 1 and 10 seconds")
    return args


def all_off(pca):
    for ch in CHANNELS:
        pca.channels[ch].duty_cycle = 0


def sweep(pca, max_duties, start_frac, end_frac, duration):
    steps = max(1, int(duration / STEP_S))
    for i in range(steps + 1):
        frac = start_frac + (end_frac - start_frac) * (i / steps)
        for ch in CHANNELS:
            pca.channels[ch].duty_cycle = int(max_duties[ch] * frac)
        time.sleep(STEP_S)


def main():
    args = parse_args()
    max_duties = {
        2: int(65535 * args.ch2_pct / 100),
        4: int(65535 * args.ch4_pct / 100),
    }
    i2c = busio.I2C(SCL, SDA)
    pca = PCA9685(i2c)
    pca.frequency = 1000

    for ch in range(16):
        pca.channels[ch].duty_cycle = 0

    print("Synchronized sweep, channels 2 and 4 together:")
    print(f"  ch2 max = {max_duties[2]} ({args.ch2_pct:g}%)")
    print(f"  ch4 max = {max_duties[4]} ({args.ch4_pct:g}%)")
    print(f"  ramp up in {args.duration:g}s, ramp down in {args.duration:g}s")
    print("Ctrl+C to stop.\n")

    try:
        while True:
            all_off(pca)
            print(f"{time.strftime('%H:%M:%S')}  ch2 + ch4  sweep UP")
            sweep(pca, max_duties, 0.0, 1.0, args.duration)

            print(f"{time.strftime('%H:%M:%S')}  ch2 + ch4  sweep DOWN")
            sweep(pca, max_duties, 1.0, 0.0, args.duration)

            all_off(pca)
            print(f"{time.strftime('%H:%M:%S')}  ch2 + ch4  OFF")
    except KeyboardInterrupt:
        print("\nStopping…")
    finally:
        all_off(pca)
        pca.deinit()
        print("Channels 2 and 4 off.")


if __name__ == "__main__":
    main()
