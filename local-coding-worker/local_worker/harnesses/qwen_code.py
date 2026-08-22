from __future__ import annotations

import json
from typing import Any

from ..service import AdapterError
from .base import OneShotHarnessAdapter


class QwenCodeAdapter(OneShotHarnessAdapter):
    adapter_name = "qwen-code"

    def __init__(self, binary: str = "qwen", **kwargs) -> None:
        super().__init__(binary, **kwargs)

    def build_command(self, session: dict[str, Any], prompt: str) -> tuple[list[str], dict[str, str]]:
        config = session["config"]
        argv = [
            session["binary"], "--prompt", prompt, "--output-format", "json", "--safe-mode",
            "--approval-mode", "plan", "--exclude-tools", "agent,shell,write,edit",
            "--max-session-turns", str(int(config.get("max_session_turns", 12))),
            "--max-wall-time", str(int(config.get("max_wall_time_seconds", 600))),
            "--max-tool-calls", str(int(config.get("max_tool_calls", 25))),
        ]
        if config.get("model"):
            argv.extend(["--model", str(config["model"])])
        return argv, {"QWEN_RUNTIME_DIR": str(session["runtime"])}

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
        return str(result.get("result", "")), dict(result.get("usage") or {})
