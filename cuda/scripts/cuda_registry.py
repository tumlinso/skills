#!/usr/bin/env python3
"""Dependency-free validation for registered CUDA benchmark campaigns."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any


class RegistryError(ValueError):
    """Raised when a CUDA benchmark registry is malformed."""


_PARAMETER_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_PLACEHOLDER = re.compile(r"\{parameter:([A-Za-z][A-Za-z0-9_]{0,63})\}")


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


def _safe_dataset_value(value: str, name: str) -> str:
    """Allow only a registered, project-relative data reference."""
    return _relative_pattern(value, name)


def normalize_datasets(value: object | None, name: str) -> dict[str, Any]:
    datasets = _object(value or {}, name)
    result: dict[str, Any] = {}
    for source, raw in datasets.items():
        if not isinstance(source, str) or not _PARAMETER_NAME.fullmatch(source):
            raise RegistryError(f"{name} source names must be identifiers")
        item = _object(raw, f"{name}.{source}")
        _extra(item, {"root", "entries"}, f"{name}.{source}")
        root = _safe_dataset_value(_string(item.get("root"), f"{name}.{source}.root"), f"{name}.{source}.root")
        entries = _object(item.get("entries"), f"{name}.{source}.entries")
        if not entries:
            raise RegistryError(f"{name}.{source}.entries must not be empty")
        normalized = {}
        for entry, path in entries.items():
            if not isinstance(entry, str) or not entry:
                raise RegistryError(f"{name}.{source}.entries keys must be non-empty strings")
            relative = _safe_dataset_value(_string(path, f"{name}.{source}.entries.{entry}"), f"{name}.{source}.entries.{entry}")
            normalized[entry] = f"{root}/{relative}"
        result[source] = {"root": root, "entries": normalized}
    return result


def normalize_parameters(value: object | None, name: str, datasets: dict[str, Any]) -> dict[str, Any]:
    """Normalize the deliberately small, argv-only probe parameter vocabulary."""
    parameters = _object(value or {}, name)
    result: dict[str, Any] = {}
    for key, raw in parameters.items():
        if not isinstance(key, str) or not _PARAMETER_NAME.fullmatch(key):
            raise RegistryError(f"{name} parameter names must be identifiers")
        item = _object(raw, f"{name}.{key}")
        _extra(item, {"type", "default", "minimum", "maximum", "values", "source"}, f"{name}.{key}")
        kind = _string(item.get("type"), f"{name}.{key}.type")
        if kind not in {"integer", "number", "enum", "dataset"}:
            raise RegistryError(f"{name}.{key}.type must be integer, number, enum, or dataset")
        normalized: dict[str, Any] = {"type": kind}
        if kind in {"integer", "number"}:
            minimum = item.get("minimum")
            maximum = item.get("maximum")
            if minimum is not None:
                normalized["minimum"] = _number(minimum, f"{name}.{key}.minimum", minimum=float("-inf"))
            if maximum is not None:
                normalized["maximum"] = _number(maximum, f"{name}.{key}.maximum", minimum=float("-inf"))
            if "minimum" in normalized and "maximum" in normalized and normalized["minimum"] > normalized["maximum"]:
                raise RegistryError(f"{name}.{key}.minimum must be <= maximum")
        elif kind == "enum":
            values = item.get("values")
            if not isinstance(values, dict) or not values:
                raise RegistryError(f"{name}.{key}.values must be a non-empty object")
            normalized_values: dict[str, str] = {}
            for value_key, value in values.items():
                if not isinstance(value_key, str) or not value_key:
                    raise RegistryError(f"{name}.{key}.values keys must be non-empty strings")
                if kind == "dataset":
                    normalized_values[value_key] = _safe_dataset_value(_string(value, f"{name}.{key}.values.{value_key}"), f"{name}.{key}.values.{value_key}")
                else:
                    normalized_values[value_key] = _string(value, f"{name}.{key}.values.{value_key}")
            normalized["values"] = normalized_values
        else:
            source = _string(item.get("source"), f"{name}.{key}.source")
            if source not in datasets:
                raise RegistryError(f"{name}.{key}.source must name a registered dataset source")
            normalized["source"] = source
            normalized["values"] = dict(datasets[source]["entries"])
        if "default" in item:
            # Validate now, but retain the symbolic/default caller value for
            # evidence.  Expansion resolves dataset symbols only at execution.
            normalize_parameter_values({key: item["default"]}, {key: normalized})
            normalized["default"] = item["default"]
        result[key] = normalized
    return result


def normalize_parameter_values(values: object | None, declarations: dict[str, Any]) -> dict[str, str]:
    """Validate caller values and render them as inert argv component text."""
    supplied = _object(values or {}, "parameters")
    unknown = sorted(set(supplied) - set(declarations))
    if unknown:
        raise RegistryError(f"parameters contains undeclared values: {', '.join(unknown)}")
    result: dict[str, str] = {}
    for name, declaration in declarations.items():
        if name not in supplied:
            if "default" not in declaration:
                raise RegistryError(f"parameters.{name} is required")
            value = declaration["default"]
        else:
            value = supplied[name]
        kind = declaration["type"]
        if kind == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise RegistryError(f"parameters.{name} must be an integer")
            numeric: float = float(value)
            rendered = str(value)
        elif kind == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise RegistryError(f"parameters.{name} must be a finite number")
            numeric = float(value)
            rendered = format(numeric, ".15g")
        else:
            if not isinstance(value, str) or value not in declaration["values"]:
                raise RegistryError(f"parameters.{name} must name a registered {kind} value")
            result[name] = str(declaration["values"][value])
            continue
        if "minimum" in declaration and numeric < declaration["minimum"]:
            raise RegistryError(f"parameters.{name} is below minimum")
        if "maximum" in declaration and numeric > declaration["maximum"]:
            raise RegistryError(f"parameters.{name} is above maximum")
        result[name] = rendered
    return result


def expand_parameter_argv(argv: list[str], values: dict[str, str]) -> list[str]:
    """Expand only declared placeholders inside an already registered argv."""
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            raise RegistryError(f"argv references undeclared parameter {name}")
        return values[name]
    result = []
    for item in argv:
        expanded = _PLACEHOLDER.sub(replace, item)
        if "{parameter:" in expanded:
            raise RegistryError("argv contains unresolved parameter placeholder")
        result.append(expanded)
    return result


def normalize_campaign(value: object, position: int = 0) -> dict[str, Any]:
    name = f"campaigns[{position}]"
    campaign = _object(value, name)
    _extra(campaign, {
        "id", "description", "targets", "paths", "symbols", "task_ids", "task_prefixes",
        "build", "correctness", "benchmark", "metric", "resources", "policy", "compatibility", "parameters", "datasets", "binary_paths",
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
        "datasets": normalize_datasets(campaign.get("datasets"), f"{name}.datasets"),
    }
    result["parameters"] = normalize_parameters(campaign.get("parameters"), f"{name}.parameters", result["datasets"])
    result["binary_paths"] = sorted(_relative_pattern(item, f"{name}.binary_paths") for item in _strings(campaign.get("binary_paths", []), f"{name}.binary_paths"))
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


def campaign_probe_spec(registry: dict[str, Any], campaign_id: str, *, mode: str,
                        parameters: object | None = None, rebuild: bool = False) -> dict[str, Any]:
    """Compile a registered campaign into the narrow foreground measurement contract.

    This deliberately does not accept argv, environment, paths, or arbitrary
    recipes from the caller.  The returned structure is suitable only for the
    controller's registered-probe adapter.
    """
    if mode not in {"benchmark", "nsys", "ncu"}:
        raise RegistryError("probe mode must be benchmark, nsys, or ncu")
    campaign = next((item for item in registry["campaigns"] if item["id"] == campaign_id), None)
    if campaign is None:
        raise RegistryError(f"unknown registry campaign: {campaign_id}")
    if not campaign["binary_paths"]:
        raise RegistryError(f"campaign {campaign_id} must declare binary_paths for foreground probing")
    values = normalize_parameter_values(parameters, campaign["parameters"])
    effective_parameters = {
        name: parameters[name] if isinstance(parameters, dict) and name in parameters else declaration.get("default")
        for name, declaration in campaign["parameters"].items()
    }
    expand = lambda command: expand_parameter_argv(list(command["argv"]), values)
    benchmark = campaign["benchmark"]
    benchmark_argv = expand(benchmark)
    spec: dict[str, Any] = {
        "schema_version": 1,
        "project_root": registry["project_root"],
        "campaign_id": campaign["id"],
        "recipe": "baseline" if mode == "benchmark" else mode,
        "argv": benchmark_argv,
        "correctness_argv": expand(campaign["correctness"]),
        "correctness_timeout": campaign["correctness"]["timeout_seconds"],
        "metric": campaign["metric"]["path"],
        "direction": campaign["metric"]["direction"],
        "warmups": benchmark["warmups"],
        "repetitions": benchmark["repetitions"],
        "timeout": benchmark["timeout_seconds"],
        "practical_regression_percent": campaign["metric"]["practical_regression_percent"],
        "target": campaign["metric"]["target"],
        "compatibility": campaign["compatibility"],
        "paths": campaign["paths"],
        "binary_paths": expand_parameter_argv(campaign["binary_paths"], values),
        "inputs": sorted(values[name] for name, declaration in campaign["parameters"].items()
                         if declaration["type"] == "dataset"),
        "resources": {
            "gpus": campaign["resources"]["gpu_count"],
            "gpu_uuids": campaign["resources"]["gpu_uuids"],
            "architecture": campaign["resources"].get("architecture"),
            # A pair occupies its NVLink interference domain.  PCIe-root is
            # topology evidence, not a required host-wide exclusion.
            "isolate_pcie_root": campaign["resources"]["isolate_pcie_root"],
            "isolate_nvlink_domain": True,
        },
        "effective_parameters": effective_parameters,
    }
    if rebuild:
        if campaign["build"] is None:
            raise RegistryError(f"campaign {campaign_id} has no registered build recipe")
        spec["benchmark"] = {"build_argv": expand(campaign["build"])}
        spec["build_timeout"] = campaign["build"]["timeout_seconds"]
    return spec
