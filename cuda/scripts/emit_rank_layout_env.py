#!/usr/bin/env python3
"""Emit simple environment hints for preferred V100 rank layouts."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpus", type=int, choices=(2, 4), required=True)
    parser.add_argument("--pair", choices=("a", "b"), default="a")
    args = parser.parse_args()

    if args.gpus == 2:
        visible = "0,2" if args.pair == "a" else "1,3"
    else:
        visible = "0,2,1,3"

    print(f"CUDA_VISIBLE_DEVICES={visible}")
    print("Recommendation: one process per GPU")
    if args.gpus == 4:
        print("Preferred groups: {0,2} and {1,3}")


if __name__ == "__main__":
    main()
