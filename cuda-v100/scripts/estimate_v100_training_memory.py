#!/usr/bin/env python3
"""Rough V100 training memory estimator."""

from __future__ import annotations

import argparse


def gib(value: float) -> float:
    return value / (1024 ** 3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=float, required=True, help="Parameter count")
    parser.add_argument("--param-bytes", type=int, default=2)
    parser.add_argument("--grad-bytes", type=int, default=2)
    parser.add_argument("--optimizer-multiplier", type=float, default=4.0)
    parser.add_argument("--activation-bytes", type=float, default=0.0, help="Estimated activation bytes")
    parser.add_argument("--workspace-bytes", type=float, default=0.0)
    parser.add_argument("--extra-bytes", type=float, default=0.0)
    args = parser.parse_args()

    params = args.params * args.param_bytes
    grads = args.params * args.grad_bytes
    opt = args.params * args.optimizer_multiplier
    total = params + grads + opt + args.activation_bytes + args.workspace_bytes + args.extra_bytes

    print(f"params_gib={gib(params):.3f}")
    print(f"grads_gib={gib(grads):.3f}")
    print(f"optimizer_gib={gib(opt):.3f}")
    print(f"activations_gib={gib(args.activation_bytes):.3f}")
    print(f"workspace_gib={gib(args.workspace_bytes):.3f}")
    print(f"extra_gib={gib(args.extra_bytes):.3f}")
    print(f"total_gib={gib(total):.3f}")
    print(f"fits_v100_16gb={'yes' if gib(total) < 16.0 else 'no'}")


if __name__ == "__main__":
    main()
