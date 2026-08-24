from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from ..service import AdapterError
from ..result_validation import ModelOutcomeError, validate_model_outcome
from .base import OneShotHarnessAdapter
from ..telemetry import qwen_harness_telemetry


class QwenCodeAdapter(OneShotHarnessAdapter):
    adapter_name = "qwen-code"

    def __init__(self, binary: str = "qwen", **kwargs) -> None:
        super().__init__(binary, **kwargs)

    def build_command(self, session: dict[str, Any], prompt: str) -> tuple[list[str], dict[str, str]]:
        config = session["config"]
        base_url = config.get("base_url")
        model = config.get("model")
        if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
            raise AdapterError("qwen-code requires an explicit local base_url")
        if not isinstance(model, str) or not model:
            raise AdapterError("qwen-code requires an explicit local model id")
        qwen_home = Path(tempfile.mkdtemp(prefix="qwen-home-", dir=session["runtime"]))
        api_key_name = "CORE4_LOCAL_API_KEY"
        mode = str(config.get("mode", "readonly"))
        writable = mode == "writable"
        approval = "auto-edit" if writable else "plan"
        allowed = (["read_file", "list_directory", "glob", "grep_search", "edit", "write_file", "structured_output"]
                   if writable else ["read_file", "list_directory", "glob", "grep_search", "structured_output"])
        requested = config.get("allowed_tools")
        if requested is not None:
            if not isinstance(requested, list) or any(not isinstance(item, str) or item not in allowed for item in requested):
                raise AdapterError("qwen-code allowed_tools exceed the mode policy")
            allowed = requested
        settings = {
            "modelProviders": {"openai": [{
                "id": model, "name": model, "envKey": api_key_name, "baseUrl": base_url,
            }]},
            "security": {"auth": {"selectedType": "openai"}},
            "model": {"name": model},
            "tools": {"approvalMode": approval},
            "skills": {"disabled": ["*"]},
            "disableAllHooks": True,
            "mcpServers": {},
        }
        (qwen_home / "settings.json").write_text(json.dumps(settings, sort_keys=True) + "\n", encoding="utf-8")
        schema = Path(__file__).resolve().parents[2] / "schemas" / "model-outcome-v1.schema.json"
        excluded = ("agent,shell,run_shell_command" if writable else
                    "agent,shell,run_shell_command,write,edit,write_file")
        argv = [
            session["binary"], "--prompt", prompt, "--output-format", "json", "--bare",
            "--auth-type", "openai", "--openai-api-key", "core4-local", "--openai-base-url", base_url,
            "--approval-mode", approval, "--allowed-tools", ",".join(allowed),
            "--exclude-tools", excluded, "--json-schema", f"@{schema}",
            "--max-session-turns", str(int(config.get("max_session_turns", 7))),
            "--max-wall-time", str(int(config.get("max_wall_time_seconds", 180))),
            "--max-tool-calls", str(int(config.get("max_tool_calls", 10 if writable else 8))),
            "--max-subagent-depth", "1",
            "--model", model,
        ]
        return argv, {
            "HOME": str(qwen_home), "QWEN_RUNTIME_DIR": str(session["runtime"]),
            "QWEN_HOME": str(qwen_home), api_key_name: "core4-local",
            "CORE4_LOCAL_BASE_URL": base_url, "CORE4_LOCAL_MODEL": model,
        }

    def build_environment(self, session: dict[str, Any], adapter_env: dict[str, str]) -> dict[str, str]:
        allowed_names = {"PATH", "LANG", "TMPDIR", "CUDA_VISIBLE_DEVICES"}
        configured = session["config"].get("environment_allowlist", [])
        if not isinstance(configured, list) or any(not isinstance(item, str) for item in configured):
            raise AdapterError("environment_allowlist must be a string array")
        allowed_names.update(configured)
        environment = {
            key: value for key, value in os.environ.items()
            if key in allowed_names or key.startswith("LC_")
        }
        environment.update(adapter_env)
        return environment

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
        payload = result.get("result", "")
        text = json.dumps(payload, separators=(",", ":")) if isinstance(payload, dict) else str(payload)
        usage = dict(result.get("usage") or {})
        usage["core4"] = qwen_harness_telemetry(records)
        return text, usage

    def normalize_outcome(
        self, text: str, usage: dict[str, Any], session: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        telemetry = dict(usage.get("core4") or {})
        terminal = str(telemetry.get("terminal_reason", "")).lower()
        if telemetry.get("budget_exhausted"):
            return {"status": "needs_codex", "outcome": "NEEDS_CODEX", "reason": "harness_budget_exhausted"}
        if telemetry.get("preempted"):
            return {"status": "preempted", "outcome": "NEEDS_CODEX", "reason": "resource_preempted"}
        config = {} if session is None else session["config"]
        try:
            value = json.loads(text)
            if isinstance(value, dict):
                root = Path(config.get("repository_root", config.get("cwd", "."))).resolve()
                claims = value.get("claims")
                if isinstance(claims, list):
                    for claim in claims:
                        evidence = claim.get("evidence") if isinstance(claim, dict) else None
                        if not isinstance(evidence, list):
                            continue
                        for item in evidence:
                            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                                continue
                            candidate = Path(item["path"])
                            if candidate.is_absolute():
                                try:
                                    item["path"] = candidate.resolve().relative_to(root).as_posix()
                                except ValueError:
                                    pass
                if str(config.get("mode", "readonly")) == "readonly":
                    value["changed_paths"] = []
            outcome = validate_model_outcome(
                value,
                repository_root=config.get("repository_root", config.get("cwd", ".")),
                authorized_read_paths=list(config.get("authorized_read_paths", ["."])),
                write_paths=list(config.get("write_paths", [])),
                actual_changed_paths=list(config.get("actual_changed_paths", [])),
                mode=str(config.get("mode", "readonly")),
                pure_test_plan=bool(config.get("pure_test_plan", False)),
            )
        except (json.JSONDecodeError, ModelOutcomeError, TypeError, ValueError) as error:
            return {"status": "needs_codex", "outcome": "NEEDS_CODEX", "reason": f"invalid_model_outcome: {error}"}
        status = {"completed": "succeeded", "needs_codex": "needs_codex", "failed": "failed"}[outcome["outcome"]]
        return {"status": status, "outcome": outcome["outcome"].upper(), "model_outcome": outcome}
