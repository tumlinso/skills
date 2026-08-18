#!/usr/bin/env python3
"""Emit baseline NVHPC compile commands for common modes."""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("cuda", "openacc", "openmp", "stdpar"), required=True)
    args = parser.parse_args()

    if args.mode == "cuda":
        print("nvc++ -O3 -std=c++17 -cuda -gpu=cc70 -Minfo=accel your_file.cpp -o your_bin")
    elif args.mode == "openacc":
        print("nvc++ -O3 -std=c++17 -acc -gpu=cc70 -Minfo=accel your_file.cpp -o your_bin")
    elif args.mode == "openmp":
        print("nvc++ -O3 -std=c++17 -mp=gpu -gpu=cc70 -Minfo=mp your_file.cpp -o your_bin")
    else:
        print("nvc++ -O3 -std=c++17 -stdpar -gpu=cc70 your_file.cpp -o your_bin")


if __name__ == "__main__":
    main()
