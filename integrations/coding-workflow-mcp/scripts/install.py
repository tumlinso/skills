#!/usr/bin/env python3
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
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=check, shell=False)


def main() -> None:
    package_root = Path(__file__).resolve().parents[1]
    skills_root = package_root.parents[1]
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")).expanduser()
    venv_root = data_home / "coding-workflow-mcp" / "venv"
    venv_root.parent.mkdir(parents=True, exist_ok=True)
    if not (venv_root / "bin" / "python").exists():
        venv.EnvBuilder(with_pip=True).create(venv_root)
    python = venv_root / "bin" / "python"
    run([str(python), "-m", "pip", "install", "--upgrade", "-r", str(package_root / "requirements.lock")])
    run([str(python), "-m", "pip", "install", "--upgrade", str(package_root)])

    codex = shutil.which("codex")
    if not codex:
        raise SystemExit("codex CLI is not available")
    existing = run([codex, "mcp", "get", SERVER_NAME], check=False)
    if existing.returncode == 0:
        run([codex, "mcp", "remove", SERVER_NAME])
    run([
        codex, "mcp", "add", SERVER_NAME,
        "--env", f"CODING_WORKFLOW_SKILLS_ROOT={skills_root}",
        "--", str(python), "-m", "coding_workflow_mcp",
    ])
    listed = run([codex, "mcp", "list"])
    if SERVER_NAME not in listed.stdout:
        raise SystemExit("coding-workflow was not present in codex mcp list")
    smoke = run([
        str(python), "-m", "coding_workflow_mcp.protocol",
        "--command", str(python), "--skills-root", str(skills_root),
    ])
    result = json.loads(smoke.stdout)
    print(json.dumps({
        "status": "installed", "server": SERVER_NAME, "venv": str(venv_root),
        "skills_root": str(skills_root), "protocol": result,
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()

