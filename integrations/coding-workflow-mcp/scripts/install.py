#!/usr/bin/env python3
"""Idempotent install with MCP registration rollback."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv


SERVER_NAME = "coding-workflow"


def run(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check, shell=False,
    )


def _registration_args(codex: str, registration: dict[str, object]) -> list[str]:
    transport = registration.get("transport")
    if not isinstance(transport, dict) or transport.get("type") != "stdio":
        raise RuntimeError("only stdio coding-workflow registrations can be restored automatically")
    command = transport.get("command")
    args = transport.get("args", [])
    env = transport.get("env", {})
    if not isinstance(command, str) or not isinstance(args, list) or not isinstance(env, dict):
        raise RuntimeError("prior MCP registration is malformed")
    result = [codex, "mcp", "add", SERVER_NAME]
    for key, value in sorted(env.items()):
        result.extend(["--env", f"{key}={value}"])
    return [*result, "--", command, *[str(item) for item in args]]


def _read_registration(codex: str) -> dict[str, object] | None:
    result = run([codex, "mcp", "get", SERVER_NAME, "--json"], check=False)
    if result.returncode:
        return None
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("prior MCP registration is not an object")
    return value


def install() -> dict[str, object]:
    package_root = Path(__file__).resolve().parents[1]
    skills_root = package_root.parents[1]
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")).expanduser()
    install_root = data_home / "coding-workflow-mcp"
    venv_root = install_root / "venv"
    install_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not (venv_root / "bin" / "python").exists():
        venv.EnvBuilder(with_pip=True).create(venv_root)
    python = venv_root / "bin" / "python"
    run([str(python), "-m", "pip", "install", "--upgrade", "-r", str(package_root / "requirements.lock")])
    run([str(python), "-m", "pip", "install", "--upgrade", str(package_root)])

    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI is not available")
    prior = _read_registration(codex)
    rollback_file = install_root / "registration.rollback.json"
    if prior is not None:
        rollback_file.write_text(json.dumps(prior, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(rollback_file, 0o600)
    try:
        if prior is not None:
            run([codex, "mcp", "remove", SERVER_NAME])
        run([
            codex, "mcp", "add", SERVER_NAME,
            "--env", f"CODING_WORKFLOW_SKILLS_ROOT={skills_root}",
            "--", str(python), "-m", "coding_workflow_mcp",
        ])
        listed = json.loads(run([codex, "mcp", "list", "--json"]).stdout)
        if SERVER_NAME not in json.dumps(listed):
            raise RuntimeError("coding-workflow was not present in codex mcp list")
        smoke = json.loads(run([
            str(python), "-m", "coding_workflow_mcp.protocol",
            "--command", str(python), "--skills-root", str(skills_root),
        ]).stdout)
        if not smoke.get("ok"):
            raise RuntimeError("installed MCP initialization smoke failed")
    except Exception:
        run([codex, "mcp", "remove", SERVER_NAME], check=False)
        if prior is not None:
            run(_registration_args(codex, prior))
        raise
    return {
        "status": "installed", "server": SERVER_NAME, "venv": str(venv_root),
        "skills_root": str(skills_root), "protocol": smoke,
        "rollback_registration": str(rollback_file) if prior is not None else None,
    }


def main() -> None:
    try:
        result = install()
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": type(exc).__name__}, sort_keys=True, separators=(",", ":")))
        raise SystemExit(2) from None
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
