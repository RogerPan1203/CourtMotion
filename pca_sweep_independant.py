#!/usr/bin/env python3
"""
Configurable synchronized motor sweep on two selected PCA9685 channels.

Both outputs are driven together. Defaults are channel 2 at 30% and channel 4
at 30%, with independently validated command-line settings.

Each selected channel: 0 → 30% over 3s, then 30% → 0 over 3s
Then repeat.

Ctrl+C to stop (both channels off on exit).
"""

import argparse
import time
import busio
from board import SCL, SDA
from adafruit_pca9685 import PCA9685

STEP_S = 0.10


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel-a", type=int, default=2)
    parser.add_argument("--channel-b", type=int, default=4)
    parser.add_argument("--a-pct", "--ch2-pct", dest="a_pct", type=float, default=30.0)
    parser.add_argument("--b-pct", "--ch4-pct", dest="b_pct", type=float, default=30.0)
    parser.add_argument("--duration", type=float, default=3.0)
    args = parser.parse_args()
    for name in ("channel_a", "channel_b"):
        if not 1 <= getattr(args, name) <= 6:
            parser.error(f"{name} must be between 1 and 6")
    if args.channel_a == args.channel_b:
        parser.error("choose two different channels")
    for name in ("a_pct", "b_pct"):
        if not 0 <= getattr(args, name) <= 30:
            parser.error(f"{name} must be between 0 and 30 percent")
    if not 1 <= args.duration <= 10:
        parser.error("duration must be between 1 and 10 seconds")
    return args


def all_off(pca):
    for ch in range(16):
        pca.channels[ch].duty_cycle = 0


def sweep(pca, max_duties, start_frac, end_frac, duration):
    steps = max(1, int(duration / STEP_S))
    for i in range(steps + 1):
        frac = start_frac + (end_frac - start_frac) * (i / steps)
        for ch in max_duties:
            pca.channels[ch].duty_cycle = int(max_duties[ch] * frac)
        time.sleep(STEP_S)


def main():
    args = parse_args()
    max_duties = {
        args.channel_a: int(65535 * args.a_pct / 100),
        args.channel_b: int(65535 * args.b_pct / 100),
    }
    i2c = busio.I2C(SCL, SDA)
    pca = PCA9685(i2c)
    pca.frequency = 1000

    for ch in range(16):
        pca.channels[ch].duty_cycle = 0

    print(f"Synchronized sweep, channels {args.channel_a} and {args.channel_b} together:")
    print(f"  ch{args.channel_a} max = {max_duties[args.channel_a]} ({args.a_pct:g}%)")
    print(f"  ch{args.channel_b} max = {max_duties[args.channel_b]} ({args.b_pct:g}%)")
    print(f"  ramp up in {args.duration:g}s, ramp down in {args.duration:g}s")
    print("Ctrl+C to stop.\n")

    try:
        while True:
            all_off(pca)
            print(f"{time.strftime('%H:%M:%S')}  ch{args.channel_a} + ch{args.channel_b}  sweep UP")
            sweep(pca, max_duties, 0.0, 1.0, args.duration)

            print(f"{time.strftime('%H:%M:%S')}  ch{args.channel_a} + ch{args.channel_b}  sweep DOWN")
            sweep(pca, max_duties, 1.0, 0.0, args.duration)

            all_off(pca)
            print(f"{time.strftime('%H:%M:%S')}  ch{args.channel_a} + ch{args.channel_b}  OFF")
    except KeyboardInterrupt:
        print("\nStopping…")
    finally:
        all_off(pca)
        pca.deinit()
        print("All channels off.")


if __name__ == "__main__":
    main()
