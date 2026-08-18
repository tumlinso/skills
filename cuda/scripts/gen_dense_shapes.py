#!/usr/bin/env python3
"""Generate dense benchmark manifests for V100-focused experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_cases(preset: str) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []

    if preset in {"all", "alignment"}:
        cases.extend(
            [
                {"name": "gemm_aligned_4096", "kind": "gemm", "m": 4096, "n": 4096, "k": 4096, "dtype": "fp16"},
                {"name": "gemm_misaligned_4093", "kind": "gemm", "m": 4093, "n": 4093, "k": 4093, "dtype": "fp16"},
                {"name": "gemm_tall_skinny", "kind": "gemm", "m": 32768, "n": 512, "k": 1024, "dtype": "fp16"},
                {"name": "gemm_batched_small", "kind": "batched_gemm", "batch": 256, "m": 128, "n": 128, "k": 128, "dtype": "fp16"},
            ]
        )

    if preset in {"all", "transformer"}:
        cases.extend(
            [
                {"name": "qkv_projection_aligned", "kind": "gemm", "m": 4096, "n": 3072, "k": 1024, "dtype": "fp16"},
                {"name": "qkv_projection_misaligned", "kind": "gemm", "m": 4096, "n": 3073, "k": 1021, "dtype": "fp16"},
                {"name": "attention_scores", "kind": "batched_gemm", "batch": 128, "m": 128, "n": 128, "k": 64, "dtype": "fp16"},
                {"name": "attention_apply", "kind": "batched_gemm", "batch": 128, "m": 128, "n": 64, "k": 128, "dtype": "fp16"},
                {"name": "mlp_up_proj", "kind": "gemm", "m": 4096, "n": 4096, "k": 1024, "dtype": "fp16"},
                {"name": "mlp_down_proj", "kind": "gemm", "m": 4096, "n": 1024, "k": 4096, "dtype": "fp16"},
            ]
        )

    if preset in {"all", "diffusers"}:
        cases.extend(
            [
                {"name": "unet_proj_in", "kind": "gemm", "m": 16384, "n": 320, "k": 320, "dtype": "fp16"},
                {"name": "unet_proj_out", "kind": "gemm", "m": 16384, "n": 320, "k": 1280, "dtype": "fp16"},
                {"name": "cross_attn_qk", "kind": "batched_gemm", "batch": 80, "m": 77, "n": 4096, "k": 64, "dtype": "fp16"},
                {"name": "cross_attn_av", "kind": "batched_gemm", "batch": 80, "m": 4096, "n": 64, "k": 77, "dtype": "fp16"},
            ]
        )

    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", choices=["all", "alignment", "transformer", "diffusers"], default="all")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = {
        "preset": args.preset,
        "notes": [
            "These are benchmark manifests for V100-oriented experiments.",
            "Prefer aligned FP16 shapes first, then compare against deliberately misaligned variants.",
            "Use them to drive project-specific microbenchmarks, cuBLASLt sweeps, or profiler wrappers.",
        ],
        "cases": build_cases(args.preset),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
