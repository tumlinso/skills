#!/usr/bin/env python3
"""Merge source-specific paper hit outputs into one normalized hit set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import dedupe_hits, read_json


def load_hits(paths: list[Path]) -> list[dict]:
    merged: list[dict] = []
    for path in paths:
        payload = read_json(path)
        if isinstance(payload, dict) and "hits" in payload:
            merged.extend(payload["hits"])
        elif isinstance(payload, list):
            merged.extend(payload)
        else:
            raise ValueError(f"Unsupported hit payload in {path}")
    return dedupe_hits(merged)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Source hit JSON files")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    payload = {"hits": load_hits([Path(item) for item in args.paths])}
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
