#!/usr/bin/env python3
"""Deterministic changed-code matching for CUDA benchmark registries."""

from __future__ import annotations

import fnmatch
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from cuda_registry import RegistryError, campaign_watch_spec, normalize_registry


def _strings(value: object, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise RegistryError(f"{name} must be a list of non-empty strings")
    return sorted(set(value))


def _path(value: str, name: str) -> str:
    normalized = value.replace("\\", "/")
    if normalized.startswith("/") or ".." in PurePosixPath(normalized).parts:
        raise RegistryError(f"{name} must contain safe repository-relative paths or globs")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        raise RegistryError(f"{name} must contain safe repository-relative paths or globs")
    return normalized


def _accepted_paths(value: object) -> list[str]:
    patches = [] if value is None else value if isinstance(value, list) else [value]
    paths: set[str] = set()
    for index, raw in enumerate(patches):
        if not isinstance(raw, Mapping):
            raise RegistryError(f"accepted_patches[{index}] must be an object")
        patch = dict(raw)
        if patch.get("accepted") is not True:
            continue
        paths.update(_strings(patch.get("changed_paths"), f"accepted_patches[{index}].changed_paths"))
    return sorted(paths)


def _packet_symbols(value: object) -> list[str]:
    packets = [] if value is None else value if isinstance(value, list) else [value]
    symbols: set[str] = set()
    for index, raw in enumerate(packets):
        if not isinstance(raw, Mapping):
            raise RegistryError(f"context_packets[{index}] must be an object")
        packet = dict(raw)
        if packet.get("format") != "CTXPP-CONTEXT-PACKET/1" or packet.get("readonly") is not True:
            raise RegistryError(f"context_packets[{index}] is not a readonly CTXPP-CONTEXT-PACKET/1")
        target = packet.get("target")
        if not isinstance(target, Mapping):
            raise RegistryError(f"context_packets[{index}].target must be an object")
        for field in ("id", "name", "signature"):
            item = target.get(field)
            if isinstance(item, str) and item:
                symbols.add(item)
    return sorted(symbols)


def normalize_discovery_input(value: object | None) -> dict[str, Any]:
    request = {} if value is None else dict(value) if isinstance(value, Mapping) else None
    if request is None:
        raise RegistryError("discovery input must be an object")
    allowed = {
        "schema_version", "changed_paths", "todo_scopes", "accepted_patch", "accepted_patches",
        "context_packet", "context_packets", "targets", "task_ids",
    }
    unknown = sorted(set(request) - allowed)
    if unknown:
        raise RegistryError(f"discovery input has unknown fields: {', '.join(unknown)}")
    if request.get("schema_version", 1) != 1:
        raise RegistryError("discovery input schema_version must be 1")
    accepted = request.get("accepted_patches", request.get("accepted_patch"))
    packets = request.get("context_packets", request.get("context_packet"))
    return {
        "schema_version": 1,
        "changed_paths": sorted({_path(item, "changed_paths") for item in _strings(request.get("changed_paths"), "changed_paths")}),
        "todo_scopes": sorted({_path(item, "todo_scopes") for item in _strings(request.get("todo_scopes"), "todo_scopes")}),
        "accepted_patch_paths": sorted({_path(item, "accepted_patches.changed_paths") for item in _accepted_paths(accepted)}),
        "ctxpp_symbols": _packet_symbols(packets),
        "targets": _strings(request.get("targets"), "targets"),
        "task_ids": _strings(request.get("task_ids"), "task_ids"),
    }


def _path_matches(value: str, pattern: str) -> bool:
    value = value.rstrip("/")
    pattern = pattern.rstrip("/")
    variants = {pattern}
    pending = [pattern]
    while pending:
        item = pending.pop()
        if "**/" in item:
            collapsed = item.replace("**/", "", 1)
            if collapsed not in variants:
                variants.add(collapsed)
                pending.append(collapsed)
    if any(fnmatch.fnmatchcase(value, item) for item in variants):
        return True
    if not any(character in pattern for character in "*?[") and value.startswith(pattern + "/"):
        return True
    prefix = pattern.split("*", 1)[0].split("?", 1)[0].rstrip("/")
    return bool(prefix and (value == prefix or prefix.startswith(value + "/")))


def _reasons(campaign: dict[str, Any], request: dict[str, Any]) -> list[dict[str, str]]:
    reasons: list[dict[str, str]] = []
    for source, field in (
        ("changed_path", "changed_paths"),
        ("todo_scope", "todo_scopes"),
        ("accepted_patch", "accepted_patch_paths"),
    ):
        for value in request[field]:
            for selector in campaign["paths"]:
                if _path_matches(value, selector) or (source == "todo_scope" and _path_matches(selector, value)):
                    reasons.append({"source": source, "value": value, "selector": selector})
    for symbol in request["ctxpp_symbols"]:
        if symbol in campaign["symbols"]:
            reasons.append({"source": "ctxpp_symbol", "value": symbol, "selector": symbol})
    for target in request["targets"]:
        if target in campaign["targets"]:
            reasons.append({"source": "target", "value": target, "selector": target})
    for task_id in request["task_ids"]:
        if task_id in campaign["task_ids"]:
            reasons.append({"source": "task_id", "value": task_id, "selector": task_id})
        for prefix in campaign["task_prefixes"]:
            if task_id.startswith(prefix):
                reasons.append({"source": "task_prefix", "value": task_id, "selector": prefix})
    unique = {(item["source"], item["value"], item["selector"]): item for item in reasons}
    return [unique[key] for key in sorted(unique)]


def discover_campaigns(registry_value: object, input_value: object | None) -> dict[str, Any]:
    registry = normalize_registry(registry_value)
    request = normalize_discovery_input(input_value)
    matches = []
    for campaign in registry["campaigns"]:
        reasons = _reasons(campaign, request)
        if reasons:
            matches.append({"campaign_id": campaign["id"], "reasons": reasons})
    status = "unambiguous" if len(matches) == 1 else "ambiguous" if matches else "no_match"
    result: dict[str, Any] = {
        "format": "CUDA-CAMPAIGN-DISCOVERY/1",
        "schema_version": 1,
        "status": status,
        "auto_queue_safe": status == "unambiguous",
        "matches": matches,
        "evidence": request,
    }
    if len(matches) == 1:
        selected_id = matches[0]["campaign_id"]
        campaign = next(item for item in registry["campaigns"] if item["id"] == selected_id)
        result["selected_campaign_id"] = selected_id
        result["watch_spec"] = campaign_watch_spec(registry, campaign)
    return result
