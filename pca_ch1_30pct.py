#!/usr/bin/env python3
"""
Run PCA9685 channels 2 and 4 together with validated command-line settings.

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
    parser.add_argument("--ch2-pct", type=float, default=30.0)
    parser.add_argument("--ch4-pct", type=float, default=30.0)
    args = parser.parse_args()
    if not 0 <= args.ch2_pct <= 100:
        parser.error("channel 2 must be between 0 and 100 percent")
    if not 0 <= args.ch4_pct <= 100:
        parser.error("channel 4 must be between 0 and 100 percent")
    return args


def main():
    args = parse_args()
    duties = {
        2: int(65535 * args.ch2_pct / 100),
        4: int(65535 * args.ch4_pct / 100),
    }
    i2c = busio.I2C(SCL, SDA)
    pca = PCA9685(i2c)
    pca.frequency = 1000

    def request_stop(signum, frame):
        del signum, frame
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    for ch in range(16):
        pca.channels[ch].duty_cycle = 0

    for ch, duty in duties.items():
        pca.channels[ch].duty_cycle = duty
    print(
        f"Channel 2 set to {args.ch2_pct:g}% and channel 4 set to "
        f"{args.ch4_pct:g}% together until stopped."
    )

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping…")
    finally:
        for ch in duties:
            pca.channels[ch].duty_cycle = 0
        pca.deinit()
        print("Channels 2 and 4 off.")


if __name__ == "__main__":
    main()
