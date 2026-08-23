from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..service import AdapterError
from .base import OneShotHarnessAdapter
from ..telemetry import qwen_harness_telemetry


class QwenCodeAdapter(OneShotHarnessAdapter):
    adapter_name = "qwen-code"

    def __init__(self, binary: str = "qwen", **kwargs) -> None:
        super().__init__(binary, **kwargs)

    def build_command(self, session: dict[str, Any], prompt: str) -> tuple[list[str], dict[str, str]]:
        config = session["config"]
        qwen_home = Path(session["runtime"]) / "qwen-home"
        qwen_home.mkdir(parents=True, exist_ok=True)
        settings = {
            "tools": {"approvalMode": "plan"},
            "skills": {"disabled": ["*"]},
            "disableAllHooks": True,
            "mcpServers": {},
        }
        (qwen_home / "settings.json").write_text(json.dumps(settings, sort_keys=True) + "\n", encoding="utf-8")
        allowed = config.get("allowed_tools", ["read_file", "list_directory", "glob", "grep_search"])
        if not isinstance(allowed, list) or not allowed or any(not isinstance(item, str) or not item for item in allowed):
            raise AdapterError("qwen-code allowed_tools must be a non-empty string array")
        argv = [
            session["binary"], "--prompt", prompt, "--output-format", "json", "--safe-mode",
            "--sandbox", "--approval-mode", "plan", "--allowed-tools", ",".join(allowed),
            "--exclude-tools", "agent,shell,write,edit",
            "--max-session-turns", str(int(config.get("max_session_turns", 12))),
            "--max-wall-time", str(int(config.get("max_wall_time_seconds", 600))),
            "--max-tool-calls", str(int(config.get("max_tool_calls", 25))),
            "--max-subagent-depth", "1",
        ]
        if config.get("model"):
            argv.extend(["--model", str(config["model"])])
        return argv, {"QWEN_RUNTIME_DIR": str(session["runtime"]), "QWEN_HOME": str(qwen_home)}

    def parse_output(self, stdout: str) -> tuple[str, dict[str, Any]]:
        try:
            records = json.loads(stdout)
        except json.JSONDecodeError as error:
            raise AdapterError("qwen-code did not emit JSON") from error
        if not isinstance(records, list):
            raise AdapterError("qwen-code JSON output must be an array")
        result = next((item for item in reversed(records) if isinstance(item, dict) and item.get("type") == "result"), None)
        if result is None or result.get("is_error") is True:
            raise AdapterError("qwen-code did not emit a successful result")
        text = str(result.get("result", ""))
        usage = dict(result.get("usage") or {})
        usage["core4"] = qwen_harness_telemetry(records)
        return text, usage

    def normalize_outcome(self, text: str, usage: dict[str, Any]) -> dict[str, Any]:
        telemetry = dict(usage.get("core4") or {})
        terminal = str(telemetry.get("terminal_reason", "")).lower()
        if text.strip() == "NEEDS_CODEX" or "needs_codex" in terminal:
            return {"status": "needs_codex", "outcome": "NEEDS_CODEX"}
        if telemetry.get("budget_exhausted"):
            return {"status": "needs_codex", "outcome": "NEEDS_CODEX", "reason": "harness_budget_exhausted"}
        if telemetry.get("preempted"):
            return {"status": "preempted", "outcome": "NEEDS_CODEX", "reason": "resource_preempted"}
        return {"status": "succeeded"}
