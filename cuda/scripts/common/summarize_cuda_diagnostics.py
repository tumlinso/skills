#!/usr/bin/env python3
"""Merge compact CUDA diagnostics artifacts into one short summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_input(spec: str) -> tuple[str, Path]:
    label, sep, raw_path = spec.partition(":")
    if not sep:
        raise SystemExit(f"Invalid --input value: {spec!r}. Expected label:path.")
    return label, Path(raw_path).resolve()


def summarize_json(payload: object) -> str:
    if isinstance(payload, dict):
        parts = []
        for key in ("label", "scenario", "summary", "classification", "limiter", "status", "note"):
            if key in payload:
                parts.append(f"{key}={payload[key]}")
        if not parts:
            keys = ", ".join(sorted(payload)[:6])
            parts.append(f"keys={keys}")
        return "; ".join(parts)
    if isinstance(payload, list):
        return f"list[{len(payload)}]"
    return repr(payload)


def summarize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " | ".join(lines[:3]) if lines else "<empty>"


def load_summary(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    try:
        return summarize_json(json.loads(text))
    except json.JSONDecodeError:
        return summarize_text(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, help="label:path artifact pair.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()

    rows = []
    for spec in args.input:
        label, path = parse_input(spec)
        rows.append({"label": label, "path": str(path), "summary": load_summary(path)})

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    for row in rows:
        print(f"- {row['label']}: {row['summary']} ({row['path']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
