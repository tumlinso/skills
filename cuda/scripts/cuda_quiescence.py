#!/usr/bin/env python3
"""Bounded proof that selected GPUs are idle before uncontaminated work."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


def prove_quiescence(device_uuids: list[str], sample: Callable[[list[str]], dict[str, Any]], *,
                     timeout_seconds: float = 10.0, consecutive_idle_samples: int = 3,
                     interval_seconds: float = 0.2,
                     monotonic: Callable[[], float] = time.monotonic,
                     sleep: Callable[[float], None] = time.sleep) -> dict[str, object]:
    uuids = sorted(set(str(item) for item in device_uuids))
    required = min(64, max(1, int(consecutive_idle_samples)))
    timeout = min(60.0, max(0.0, float(timeout_seconds)))
    interval = min(5.0, max(0.01, float(interval_seconds)))
    started = monotonic()
    observations: list[dict[str, Any]] = []
    samples_observed = 0
    consecutive = 0
    while True:
        observation = sample(uuids)
        observations.append(observation)
        observations = observations[-64:]
        samples_observed += 1
        idle = bool(observation.get("idle")) and not observation.get("foreign_processes") and not observation.get("busy")
        consecutive = consecutive + 1 if idle else 0
        if consecutive >= required:
            return {
                "format": "CUDA-QUIESCENCE/1", "schema_version": 1, "state": "quiescent",
                "uncontaminated": True, "device_uuids": uuids, "required_consecutive_samples": required,
                "observed_consecutive_samples": consecutive, "elapsed_seconds": monotonic() - started,
                "samples_observed": samples_observed, "observations": observations,
            }
        elapsed = monotonic() - started
        if elapsed >= timeout:
            return {
                "format": "CUDA-QUIESCENCE/1", "schema_version": 1, "state": "timeout",
                "uncontaminated": False, "device_uuids": uuids, "required_consecutive_samples": required,
                "observed_consecutive_samples": consecutive, "elapsed_seconds": elapsed,
                "samples_observed": samples_observed, "observations": observations,
            }
        sleep(min(interval, max(0.0, timeout - elapsed)))
