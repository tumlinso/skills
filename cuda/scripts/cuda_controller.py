#!/usr/bin/env python3
"""Fail-closed tombstone for the retired CUDA controller entrypoint.

This file intentionally implements no controller operations and never imports,
starts, or falls back to the archived controller. Preserve it after cutover so
stale calls fail clearly while profiler wrappers remain available separately.
"""
from __future__ import annotations

import sys

MESSAGE = (
    "cuda_controller.py is retired for host execution. It cannot admit, inspect, "
    "launch, cancel, qualify, or report legacy controller work. Submit a bounded "
    "job with `device-scheduler job submit --payload-file <job-spec.json>` and "
    "inspect it with `device-scheduler job get|wait|logs <job-id>`. Historical "
    "controller receipts remain archival evidence only."
)

def main(argv: list[str] | None = None) -> int:
    print(MESSAGE, file=sys.stderr)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
