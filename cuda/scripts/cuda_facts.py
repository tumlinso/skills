#!/usr/bin/env python3
"""Durable, raw-evidence-backed CUDA performance facts."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


FACT_ROLES = {"accepted", "previous", "candidate", "historical"}


class FactError(ValueError):
    pass


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _file_ref(path_value: object) -> dict[str, object] | None:
    path = Path(str(path_value))
    if not path.is_file():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"kind": path.name.rsplit(".", 2)[-2] if "." in path.name else "raw", "path": str(path), "sha256": digest, "complete": True}


def build_performance_fact(*, campaign_id: str, role: str, source: Mapping[str, object],
                           compatibility: Mapping[str, object], metric: str, direction: str,
                           statistics: Mapping[str, object], classification: str,
                           records: list[Mapping[str, object]], quiescence: Mapping[str, object],
                           baseline: Mapping[str, object] | None = None,
                           created_at: float | None = None) -> dict[str, object]:
    if role not in FACT_ROLES:
        raise FactError(f"unsupported performance fact role: {role}")
    evidence = []
    for record in records:
        for field in ("stdout", "stderr"):
            reference = _file_ref(record.get(field))
            if reference:
                evidence.append(reference)
    timestamp = time.time() if created_at is None else float(created_at)
    identity = {
        "campaign_id": campaign_id,
        "source_fingerprint": str(source.get("fingerprint", "")),
        "compatibility_key": str(compatibility.get("key", "")),
        "metric": metric,
        "direction": direction,
        "statistics": dict(statistics),
        "raw_evidence": evidence,
    }
    fact = {
        "format": "CUDA-PERFORMANCE-FACT/1", "schema_version": 1,
        "fact_id": hashlib.sha256(_canonical(identity).encode("utf-8")).hexdigest(),
        "campaign_id": campaign_id, "role": role,
        "source": {
            "fingerprint": str(source.get("fingerprint", "")),
            "commit": source.get("commit") or source.get("git_head"),
            "dirty": bool(source.get("dirty", False)),
        },
        "compatibility": dict(compatibility),
        "measurement": {
            "metric": metric, "direction": direction, "statistics": dict(statistics),
            "uncontaminated": bool(quiescence.get("uncontaminated")), "quiescence": dict(quiescence),
        },
        "classification": classification,
        "baseline": dict(baseline) if baseline else None,
        "raw_evidence": evidence,
        "created_at": timestamp,
    }
    return normalize_performance_fact(fact)


def normalize_performance_fact(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise FactError("performance fact must be an object")
    fact = dict(value)
    required = {
        "format", "schema_version", "fact_id", "campaign_id", "role", "source", "compatibility",
        "measurement", "classification", "baseline", "raw_evidence", "created_at",
    }
    unknown = sorted(set(fact) - required)
    missing = sorted(required - set(fact))
    if unknown or missing:
        raise FactError(f"performance fact fields invalid; missing={missing}, unknown={unknown}")
    if fact.get("format") != "CUDA-PERFORMANCE-FACT/1" or fact.get("schema_version") != 1:
        raise FactError("performance fact must use CUDA-PERFORMANCE-FACT/1 schema_version 1")
    if fact.get("role") not in FACT_ROLES:
        raise FactError("performance fact role is unsupported")
    if not isinstance(fact.get("campaign_id"), str) or not fact["campaign_id"]:
        raise FactError("performance fact campaign id is required")
    if not isinstance(fact.get("classification"), str) or not fact["classification"]:
        raise FactError("performance fact classification is required")
    if (not isinstance(fact.get("fact_id"), str) or len(str(fact["fact_id"])) != 64
            or any(character not in "0123456789abcdef" for character in str(fact["fact_id"]))):
        raise FactError("performance fact id must be a SHA-256")
    if not isinstance(fact.get("source"), Mapping) or not isinstance(fact.get("compatibility"), Mapping):
        raise FactError("performance fact source and compatibility must be objects")
    if not fact["source"].get("fingerprint"):
        raise FactError("performance fact source fingerprint is required")
    compatibility = fact["compatibility"]
    compatibility_key = compatibility.get("key")
    if (not isinstance(compatibility_key, str) or len(compatibility_key) != 64
            or any(character not in "0123456789abcdef" for character in compatibility_key)):
        raise FactError("performance fact compatibility key must be a SHA-256")
    measurement = fact.get("measurement")
    if not isinstance(measurement, Mapping) or measurement.get("uncontaminated") is not True:
        raise FactError("performance facts require an uncontaminated measurement")
    if measurement.get("direction") not in {"minimize", "maximize"} or not measurement.get("metric"):
        raise FactError("performance fact metric and direction are invalid")
    if not isinstance(measurement.get("statistics"), Mapping) or "median" not in measurement["statistics"]:
        raise FactError("performance fact statistics require a median")
    if fact.get("baseline") is not None and not isinstance(fact.get("baseline"), Mapping):
        raise FactError("performance fact baseline must be an object or null")
    evidence = fact.get("raw_evidence")
    if not isinstance(evidence, list) or not evidence:
        raise FactError("performance facts require raw evidence references")
    for item in evidence:
        digest = item.get("sha256") if isinstance(item, Mapping) else None
        if (not isinstance(item, Mapping) or not item.get("path") or not isinstance(digest, str)
                or len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest)
                or item.get("complete") is not True):
            raise FactError("raw evidence references must be complete and hashed")
    created_at = fact.get("created_at")
    if isinstance(created_at, bool) or not isinstance(created_at, (int, float)) or created_at < 0:
        raise FactError("performance fact created_at must be a non-negative number")
    return fact


class PerformanceFactStore:
    """Small facade over BackgroundStore metadata; raw files remain authoritative."""

    def __init__(self, store: object, watch_id: str, *, limit: int = 256):
        self.store = store
        self.watch_id = watch_id
        self.limit = max(1, int(limit))
        self.key = f"performance-facts:{watch_id}"

    def list(self) -> list[dict[str, object]]:
        raw = self.store.get_meta(self.key, [])
        if not isinstance(raw, list):
            return []
        result = []
        for item in raw:
            try:
                result.append(normalize_performance_fact(item))
            except FactError:
                continue
        return result

    def append(self, fact: object) -> dict[str, object]:
        normalized = normalize_performance_fact(fact)
        existing = self.list()
        if any(item["fact_id"] == normalized["fact_id"] and item["role"] == "accepted" for item in existing):
            normalized["role"] = "accepted"
        facts = [item for item in existing if item["fact_id"] != normalized["fact_id"]]
        facts.append(normalized)
        ordered = sorted(facts, key=lambda item: (float(item["created_at"]), str(item["fact_id"])), reverse=True)
        facts = [item for item in ordered if item["role"] == "accepted"]
        facts.extend(item for item in ordered if item["role"] != "accepted")
        facts = facts[:self.limit]
        self.store.set_meta(self.key, facts)
        return normalized

    def accept(self, fact_id: str) -> dict[str, object]:
        facts = self.list()
        selected = next((item for item in facts if item["fact_id"] == fact_id), None)
        if selected is None:
            raise FactError(f"unknown performance fact: {fact_id}")
        selected["role"] = "accepted"
        self.store.set_meta(self.key, facts)
        return selected
