#!/usr/bin/env python3
"""Compatibility and decision policy for CUDA performance measurements."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any


BASELINE_ROLES = ("accepted", "previous", "historical")


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def machine_class(devices: list[dict[str, object]], topology: Mapping[str, Mapping[str, str]] | None = None) -> dict[str, object]:
    """Describe comparable hardware without pinning physical indices or UUIDs."""
    topology = topology or {}
    normalized = sorted((
        str(item.get("name", "unknown")),
        str(item.get("compute_capability", "unknown")),
        int(item.get("memory_total_mib", 0) or 0),
        str(item.get("driver_version", "unknown")),
    ) for item in devices)
    selected = {str(item.get("uuid")) for item in devices if item.get("uuid")}

    def groups(field: str) -> list[int]:
        counts: dict[str, int] = {}
        for device_id in selected:
            value = topology.get(device_id, {}).get(field)
            if value:
                counts[str(value)] = counts.get(str(value), 0) + 1
        return sorted(counts.values(), reverse=True)

    return {
        "devices": [
            {"model": model, "compute_capability": capability, "memory_total_mib": memory, "driver_version": driver}
            for model, capability, memory, driver in normalized
        ],
        "topology": {"nvlink_group_sizes": groups("nvlink_domain"), "pcie_group_sizes": groups("pcie_root")},
    }


def compatibility_descriptor(*, campaign_id: str, benchmark: Mapping[str, object],
                             machine: Mapping[str, object]) -> dict[str, object]:
    declared = dict(benchmark.get("compatibility", {})) if isinstance(benchmark.get("compatibility"), Mapping) else {}
    protocol = {
        # Command and binary identity remain provenance: candidates may use a
        # different executable while measuring the same registered campaign.
        "benchmark_id": str(benchmark.get("benchmark_id", campaign_id)),
        "metric": str(benchmark.get("metric", "")),
        "direction": str(benchmark.get("direction", "")),
        "warmups": int(benchmark.get("warmups", 1)),
        "repetitions": int(benchmark.get("repetitions", 5)),
        "declared_workload": declared,
        "workload": benchmark.get("workload_identity", declared.get("workload", declared)),
        "inputs": benchmark.get("input_identity", declared.get("inputs", {})),
        "build": benchmark.get("build_identity", declared.get("build", {})),
        "numerical_contract": benchmark.get("numerical_contract", declared.get("numerical_contract", {})),
        "correctness_class": str(benchmark.get("correctness_class", declared.get("correctness_class", "unspecified"))),
        "toolchain": benchmark.get("toolchain_identity", benchmark.get("toolchain_id", declared.get("toolchain", ""))),
    }
    body = {"campaign_id": campaign_id, "protocol": protocol, "machine": dict(machine)}
    return {**body, "key": _hash(body)}


def compatible(left: Mapping[str, object], right: Mapping[str, object]) -> bool:
    left_compatibility = left.get("compatibility", left)
    right_compatibility = right.get("compatibility", right)
    return (
        isinstance(left_compatibility, Mapping)
        and isinstance(right_compatibility, Mapping)
        and bool(left_compatibility.get("key"))
        and left_compatibility.get("key") == right_compatibility.get("key")
    )


def select_baseline(facts: list[dict[str, object]], current: Mapping[str, object], *,
                    accepted_fact_id: str | None = None) -> dict[str, object]:
    candidates = [fact for fact in facts if fact.get("role") in BASELINE_ROLES and compatible(fact, current)]
    if accepted_fact_id:
        selected = next((fact for fact in candidates if fact.get("fact_id") == accepted_fact_id), None)
        return ({"status": "compatible", "relation": "accepted", "fact": selected}
                if selected else {"status": "no_compatible_baseline", "reason": "accepted_fact_incompatible_or_missing"})
    for role in BASELINE_ROLES:
        matching = [fact for fact in candidates if fact.get("role") == role]
        if matching:
            selected = max(matching, key=lambda fact: (float(fact.get("created_at", 0)), str(fact.get("fact_id", ""))))
            return {"status": "compatible", "relation": role, "fact": selected}
    return {"status": "no_compatible_baseline", "reason": "no_exact_compatibility_key"}


def comparison_percent(current: float, baseline: float, direction: str) -> float | None:
    if baseline == 0:
        if current == 0:
            return 0.0
        return None
    return ((current - baseline) / abs(baseline) * 100.0 if direction == "minimize"
            else (baseline - current) / abs(baseline) * 100.0)


def adaptive_correctness_target(*, configured_repetitions: int, minimum_seconds: float,
                                maximum_repetitions: int, completed_records: list[Mapping[str, object]]) -> int:
    """Choose the smallest bounded count likely to satisfy both count and duration."""
    configured = max(1, int(configured_repetitions))
    maximum = max(configured, int(maximum_repetitions))
    elapsed = [float(item.get("elapsed_seconds", 0) or 0) for item in completed_records if float(item.get("elapsed_seconds", 0) or 0) > 0]
    if not elapsed or minimum_seconds <= 0:
        return configured
    estimated = math.ceil(float(minimum_seconds) / (sum(elapsed) / len(elapsed)))
    return min(maximum, max(configured, estimated))


def profiler_escalation(classification: str, *, timeline_summary: object | None = None,
                        max_profiles: int = 2) -> dict[str, object]:
    """Return a bounded profiler plan; never profile invalid or noisy measurements."""
    limit = max(0, min(2, int(max_profiles)))
    if limit == 0:
        return {"profile": None, "reason": "profiling_disabled"}
    if timeline_summary is None:
        if classification in {"material-regression", "target-missed"}:
            return {"profile": "nsys", "reason": classification}
        if classification == "severe-variance":
            return {"profile": None, "reason": "repeat_uncontaminated_measurement_first"}
        return {"profile": None, "reason": "no_actionable_performance_delta"}
    if limit < 2:
        return {"profile": None, "reason": "profile_limit_reached"}
    summary = timeline_summary if isinstance(timeline_summary, Mapping) else {}
    kernels = summary.get("top_kernels", [])
    if isinstance(kernels, list) and any(isinstance(item, Mapping) and item.get("name") for item in kernels):
        return {"profile": "ncu", "reason": "timeline_identified_hot_kernel"}
    return {"profile": None, "reason": "timeline_has_no_kernel_focus"}
