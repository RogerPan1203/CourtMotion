#!/usr/bin/env python3
"""
Run two selected PCA9685 channels together with validated command-line settings.

Both channels stay on together until the process is stopped. Defaults are
channel 2 at 30% and channel 4 at 30%.
"""

import argparse
import signal
import time
import busio
from board import SCL, SDA
from adafruit_pca9685 import PCA9685

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel-a", type=int, default=2)
    parser.add_argument("--channel-b", type=int, default=4)
    parser.add_argument("--a-pct", "--ch2-pct", dest="a_pct", type=float, default=30.0)
    parser.add_argument("--b-pct", "--ch4-pct", dest="b_pct", type=float, default=30.0)
    parser.add_argument("--disable-a", action="store_true")
    parser.add_argument("--disable-b", action="store_true")
    args = parser.parse_args()
    if args.disable_a and args.disable_b:
        parser.error("turn on Motor A or Motor B")
    for name in ("channel_a", "channel_b"):
        if not 1 <= getattr(args, name) <= 7:
            parser.error(f"{name} must be between 1 and 7")
    if not args.disable_a and not args.disable_b and args.channel_a == args.channel_b:
        parser.error("choose two different channels")
    for name in ("a_pct", "b_pct"):
        value = getattr(args, name)
        if not 0 <= value <= 100:
            parser.error(f"{name} must be between 0 and 100 percent")
    return args


def main():
    args = parse_args()
    duties = {}
    if not args.disable_a:
        duties[args.channel_a] = int(65535 * args.a_pct / 100)
    if not args.disable_b:
        duties[args.channel_b] = int(65535 * args.b_pct / 100)
    i2c = busio.I2C(SCL, SDA)
    pca = PCA9685(i2c)
    pca.frequency = 1000

    def request_stop(signum, frame):
        del signum, frame
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    try:
        for ch in range(16):
            pca.channels[ch].duty_cycle = 0
        for ch, duty in duties.items():
            pca.channels[ch].duty_cycle = duty
        active = []
        if not args.disable_a:
            active.append(f"A channel {args.channel_a} at {args.a_pct:g}%")
        if not args.disable_b:
            active.append(f"B channel {args.channel_b} at {args.b_pct:g}%")
        print(f"Running {', '.join(active)} until stopped.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping…")
    finally:
        for ch in range(16):
            pca.channels[ch].duty_cycle = 0
        pca.deinit()
        print("All channels off.")


if __name__ == "__main__":
    main()
