#!/usr/bin/env python3
"""Estimate host-to-device transfer time on PCIe Gen3 x16."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bytes", type=float, required=True, help="Bytes transferred per step")
    parser.add_argument("--bandwidth-gbps", type=float, default=12.0, help="Practical GB/s for pinned PCIe Gen3 x16")
    args = parser.parse_args()

    seconds = args.bytes / (args.bandwidth_gbps * 1e9)
    print(f"estimated_transfer_ms={seconds * 1e3:.3f}")


if __name__ == "__main__":
    main()
