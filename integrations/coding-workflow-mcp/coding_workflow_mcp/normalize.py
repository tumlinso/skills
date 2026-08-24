"""Compact, redacted normalization at the MCP boundary."""

from __future__ import annotations

import json
import re
from typing import Any


SECRET_KEY = re.compile(r"(?:^|_)(?:token|secret|password|endpoint|gpu_uuid)(?:$|_)", re.IGNORECASE)
SECRET_VALUE = re.compile(r"\b(?:toc|tos|toch|tol)_[A-Za-z0-9_-]+\b")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[redacted]" if SECRET_KEY.search(str(key)) else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return SECRET_VALUE.sub("[redacted]", value)
    return value


def bounded_text(value: str, limit: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value
    suffix = "\n...[bounded]"
    room = max(0, limit - len(suffix.encode("utf-8")))
    return encoded[:room].decode("utf-8", "ignore") + suffix


def bounded_json(value: dict[str, Any], limit: int) -> dict[str, Any]:
    clean = redact(value)
    serialized = json.dumps(clean, ensure_ascii=False, separators=(",", ":"))
    if len(serialized.encode("utf-8")) <= limit:
        return clean
    return {"status": "attention_required", "reason": "normalized_result_exceeded_budget"}

