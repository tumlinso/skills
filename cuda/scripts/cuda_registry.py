#!/usr/bin/env python3
"""Dependency-free validation for registered CUDA benchmark campaigns."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any


class RegistryError(ValueError):
    """Raised when a CUDA benchmark registry is malformed."""


def _object(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RegistryError(f"{name} must be an object")
    return dict(value)


def _extra(value: dict[str, Any], allowed: set[str], name: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise RegistryError(f"{name} has unknown fields: {', '.join(unknown)}")


def _string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"{name} must be a non-empty string")
    return value


def _strings(value: object, name: str, *, unique: bool = True) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise RegistryError(f"{name} must be a list of non-empty strings")
    if unique and len(set(value)) != len(value):
        raise RegistryError(f"{name} must not contain duplicates")
    return list(value)


def _number(value: object, name: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise RegistryError(f"{name} must be a number >= {minimum:g}")
    return float(value)


def _integer(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise RegistryError(f"{name} must be an integer >= {minimum}")
    return value


def _relative_pattern(value: str, name: str) -> str:
    normalized = value.replace("\\", "/")
    if normalized.startswith("/") or ".." in PurePosixPath(normalized).parts:
        raise RegistryError(f"{name} must be a safe repository-relative path or glob")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        raise RegistryError(f"{name} must be a safe repository-relative path or glob")
    return normalized


def normalize_command(value: object, name: str) -> dict[str, Any]:
    command = _object(value, name)
    _extra(command, {"argv", "timeout_seconds"}, name)
    argv = _strings(command.get("argv"), f"{name}.argv", unique=False)
    if not argv:
        raise RegistryError(f"{name}.argv must not be empty")
    timeout = _number(command.get("timeout_seconds", 3600), f"{name}.timeout_seconds", minimum=0.001)
    return {"argv": argv, "timeout_seconds": timeout}


def normalize_metric(value: object, name: str = "metric") -> dict[str, Any]:
    metric = _object(value, name)
    _extra(metric, {
        "format", "schema_version", "name", "path", "direction", "unit",
        "practical_regression_percent", "target",
    }, name)
    if metric.get("format") != "CUDA-METRIC/1" or metric.get("schema_version") != 1:
        raise RegistryError(f"{name} must use CUDA-METRIC/1 schema_version 1")
    result: dict[str, Any] = {
        "format": "CUDA-METRIC/1",
        "schema_version": 1,
        "name": _string(metric.get("name"), f"{name}.name"),
        "path": _string(metric.get("path"), f"{name}.path"),
        "direction": metric.get("direction"),
        "unit": _string(metric.get("unit"), f"{name}.unit"),
        "practical_regression_percent": _number(
            metric.get("practical_regression_percent", 2.0),
            f"{name}.practical_regression_percent",
        ),
    }
    if result["direction"] not in {"minimize", "maximize"}:
        raise RegistryError(f"{name}.direction must be minimize or maximize")
    target = metric.get("target")
    if target is not None:
        target = _number(target, f"{name}.target", minimum=float("-inf"))
    result["target"] = target
    return result


def normalize_resources(value: object | None, name: str) -> dict[str, Any]:
    resources = _object(value or {}, name)
    _extra(resources, {
        "gpu_count", "gpu_uuids", "architecture", "gpu_memory_headroom_mib",
        "isolate_pcie_root", "isolate_nvlink_domain", "cpu_heavy",
        "build_cpu_threads", "background_cpu_threads", "background_ram_bytes",
    }, name)
    uuids = _strings(resources.get("gpu_uuids", []), f"{name}.gpu_uuids")
    count = _integer(resources.get("gpu_count", 1), f"{name}.gpu_count", minimum=1)
    if uuids and "gpu_count" in resources:
        raise RegistryError(f"{name} may declare gpu_uuids or gpu_count, not both")
    result: dict[str, Any] = {"gpu_count": len(uuids) if uuids else count, "gpu_uuids": uuids}
    architecture = resources.get("architecture")
    if architecture is not None:
        result["architecture"] = _string(architecture, f"{name}.architecture")
    for field in ("gpu_memory_headroom_mib", "build_cpu_threads", "background_cpu_threads", "background_ram_bytes"):
        result[field] = _integer(resources.get(field, 0), f"{name}.{field}")
    for field in ("isolate_pcie_root", "isolate_nvlink_domain", "cpu_heavy"):
        item = resources.get(field, False)
        if not isinstance(item, bool):
            raise RegistryError(f"{name}.{field} must be boolean")
        result[field] = item
    return result


def normalize_campaign(value: object, position: int = 0) -> dict[str, Any]:
    name = f"campaigns[{position}]"
    campaign = _object(value, name)
    _extra(campaign, {
        "id", "description", "targets", "paths", "symbols", "task_ids", "task_prefixes",
        "build", "correctness", "benchmark", "metric", "resources", "policy", "compatibility",
    }, name)
    missing = sorted({"id", "targets", "paths", "symbols", "correctness", "benchmark", "metric", "resources"} - set(campaign))
    if missing:
        raise RegistryError(f"{name} is missing required fields: {', '.join(missing)}")
    description = campaign.get("description", "")
    if not isinstance(description, str):
        raise RegistryError(f"{name}.description must be a string")
    paths = sorted(_relative_pattern(item, f"{name}.paths") for item in _strings(campaign.get("paths", []), f"{name}.paths"))
    if len(paths) != len(set(paths)):
        raise RegistryError(f"{name}.paths must not contain equivalent duplicates")
    result: dict[str, Any] = {
        "id": _string(campaign.get("id"), f"{name}.id"),
        "description": description,
        "targets": sorted(_strings(campaign.get("targets", []), f"{name}.targets")),
        "paths": paths,
        "symbols": sorted(_strings(campaign.get("symbols", []), f"{name}.symbols")),
        "task_ids": sorted(_strings(campaign.get("task_ids", []), f"{name}.task_ids")),
        "task_prefixes": sorted(_strings(campaign.get("task_prefixes", []), f"{name}.task_prefixes")),
        "metric": normalize_metric(campaign.get("metric"), f"{name}.metric"),
        "resources": normalize_resources(campaign.get("resources"), f"{name}.resources"),
    }
    if not any(result[field] for field in ("targets", "paths", "symbols", "task_ids", "task_prefixes")):
        raise RegistryError(f"{name} requires at least one discovery selector")
    build = campaign.get("build")
    result["build"] = None if build is None else normalize_command(build, f"{name}.build")
    correctness = _object(campaign.get("correctness"), f"{name}.correctness")
    _extra(correctness, {"argv", "timeout_seconds", "repetitions", "minimum_seconds", "maximum_repetitions", "class", "correctness_class", "numerical_contract"}, f"{name}.correctness")
    result["correctness"] = normalize_command(
        {key: correctness[key] for key in ("argv", "timeout_seconds") if key in correctness},
        f"{name}.correctness",
    )
    correctness_class = _string(correctness.get("class", correctness.get("correctness_class", "unspecified")), f"{name}.correctness.class")
    deterministic = correctness_class in {"deterministic", "exact"}
    repetitions = _integer(correctness.get("repetitions", 1 if deterministic else 3), f"{name}.correctness.repetitions", minimum=1)
    maximum = _integer(correctness.get("maximum_repetitions", repetitions if deterministic else 64), f"{name}.correctness.maximum_repetitions", minimum=1)
    if maximum < repetitions:
        raise RegistryError(f"{name}.correctness.maximum_repetitions must be >= repetitions")
    result["correctness"].update(
        repetitions=repetitions,
        minimum_seconds=_number(correctness.get("minimum_seconds", 0 if deterministic else 15), f"{name}.correctness.minimum_seconds"),
        maximum_repetitions=maximum,
        correctness_class=correctness_class,
        numerical_contract=_object(correctness.get("numerical_contract", {}), f"{name}.correctness.numerical_contract"),
    )
    compatibility = _object(campaign.get("compatibility", {}), f"{name}.compatibility")
    _extra(compatibility, {"workload", "inputs", "build", "toolchain"}, f"{name}.compatibility")
    result["compatibility"] = compatibility
    benchmark = _object(campaign.get("benchmark"), f"{name}.benchmark")
    _extra(benchmark, {"argv", "timeout_seconds", "warmups", "repetitions"}, f"{name}.benchmark")
    result["benchmark"] = normalize_command(
        {key: benchmark[key] for key in ("argv", "timeout_seconds") if key in benchmark},
        f"{name}.benchmark",
    )
    result["benchmark"].update(
        warmups=_integer(benchmark.get("warmups", 1), f"{name}.benchmark.warmups"),
        repetitions=_integer(benchmark.get("repetitions", 5), f"{name}.benchmark.repetitions", minimum=1),
    )
    policy = _object(campaign.get("policy", {}), f"{name}.policy")
    _extra(policy, {
        "initial_characterization", "benchmark_completed_steps", "max_background_gpus",
        "max_deep_profiles_per_revision",
    }, f"{name}.policy")
    for field, default in (("initial_characterization", False), ("benchmark_completed_steps", True)):
        if not isinstance(policy.get(field, default), bool):
            raise RegistryError(f"{name}.policy.{field} must be boolean")
    result["policy"] = {
        "initial_characterization": policy.get("initial_characterization", False),
        "benchmark_completed_steps": policy.get("benchmark_completed_steps", True),
        "max_background_gpus": _integer(policy.get("max_background_gpus", 4), f"{name}.policy.max_background_gpus", minimum=1),
        "max_deep_profiles_per_revision": _integer(policy.get("max_deep_profiles_per_revision", 2), f"{name}.policy.max_deep_profiles_per_revision"),
    }
    return result


def normalize_registry(value: object) -> dict[str, Any]:
    registry = _object(value, "registry")
    _extra(registry, {"format", "schema_version", "project_root", "campaigns"}, "registry")
    if registry.get("format") != "CUDA-BENCHMARK-REGISTRY/1" or registry.get("schema_version") != 1:
        raise RegistryError("registry must use CUDA-BENCHMARK-REGISTRY/1 schema_version 1")
    raw_campaigns = registry.get("campaigns")
    if not isinstance(raw_campaigns, list) or not raw_campaigns:
        raise RegistryError("registry.campaigns must be a non-empty array")
    campaigns = [normalize_campaign(item, index) for index, item in enumerate(raw_campaigns)]
    ids = [str(item["id"]) for item in campaigns]
    if len(ids) != len(set(ids)):
        raise RegistryError("registry campaign ids must be unique")
    return {
        "format": "CUDA-BENCHMARK-REGISTRY/1",
        "schema_version": 1,
        "project_root": _string(registry.get("project_root"), "registry.project_root"),
        "campaigns": sorted(campaigns, key=lambda item: str(item["id"])),
    }


def load_registry(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"unable to load registry {source}: {exc}") from exc
    return normalize_registry(payload)


def campaign_watch_spec(registry: dict[str, Any], campaign: dict[str, Any]) -> dict[str, Any]:
    """Compile one normalized registry campaign into the legacy watch contract."""
    metric = campaign["metric"]
    resources = campaign["resources"]
    benchmark: dict[str, Any] = {
        "argv": campaign["benchmark"]["argv"],
        "correctness_argv": campaign["correctness"]["argv"],
        "metric": metric["path"],
        "direction": metric["direction"],
        "practical_regression_percent": metric["practical_regression_percent"],
        "target": metric["target"],
        "warmups": campaign["benchmark"]["warmups"],
        "repetitions": campaign["benchmark"]["repetitions"],
        "timeout": campaign["benchmark"]["timeout_seconds"],
        "correctness_timeout": campaign["correctness"]["timeout_seconds"],
        "correctness_repetitions": campaign["correctness"]["repetitions"],
        "correctness_minimum_seconds": campaign["correctness"]["minimum_seconds"],
        "correctness_maximum_repetitions": campaign["correctness"]["maximum_repetitions"],
        "correctness_class": campaign["correctness"]["correctness_class"],
        "numerical_contract": campaign["correctness"]["numerical_contract"],
        "compatibility": campaign["compatibility"],
        "gpus": resources["gpu_count"],
        "gpu_uuids": resources["gpu_uuids"],
    }
    if campaign["build"] is not None:
        benchmark["build_argv"] = campaign["build"]["argv"]
        benchmark["build_timeout"] = campaign["build"]["timeout_seconds"]
    mapping = {
        "architecture": "architecture",
        "gpu_memory_headroom_mib": "gpu_memory_headroom_mib",
        "isolate_pcie_root": "isolate_pcie_root",
        "isolate_nvlink_domain": "isolate_nvlink_domain",
        "cpu_heavy": "cpu_heavy",
        "build_cpu_threads": "build_cpu_threads",
        "background_cpu_threads": "background_cpu_threads",
        "background_ram_bytes": "background_ram_bytes",
    }
    for source, destination in mapping.items():
        if source in resources:
            benchmark[destination] = resources[source]
    return {
        "schema_version": 1,
        "project_root": registry["project_root"],
        "watch": {
            "task_ids": campaign["task_ids"],
            "task_prefixes": campaign["task_prefixes"],
            "paths": campaign["paths"],
            "symbols": campaign["symbols"],
        },
        "benchmark": benchmark,
        "policy": campaign["policy"],
        "registry_campaign_id": campaign["id"],
    }
