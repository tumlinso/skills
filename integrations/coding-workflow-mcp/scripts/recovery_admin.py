#!/usr/bin/env python3
"""Interactive owner-side approval for one exact live coding-workflow claim."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def canonical_repo(value: str) -> Path:
    result = subprocess.run(
        ["git", "-C", value, "rev-parse", "--show-toplevel"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        shell=False,
    )
    if result.returncode:
        raise SystemExit("repository is not a Git worktree")
    return Path(result.stdout.strip()).resolve()


def approve(repo_value: str, task_id: str, reason: str, ttl_seconds: int) -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit("manual approval requires an interactive owner terminal")
    repo = canonical_repo(repo_value)
    skills_root = Path(__file__).resolve().parents[3]
    todo = skills_root / "todo-orchestrator" / "scripts" / "todo.py"
    os.chdir(repo)
    os.execv(
        sys.executable,
        [
            sys.executable, str(todo), "recover", "live-approve", task_id,
            "--reason", reason, "--ttl-seconds", str(ttl_seconds),
            "--repo-root", str(repo), "--json",
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manually approve one exact coding-workflow live-lease recovery"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("approve")
    command.add_argument("--repo", required=True)
    command.add_argument("--task-id", required=True)
    command.add_argument("--reason", required=True)
    command.add_argument("--ttl-seconds", type=int, default=300)
    args = parser.parse_args()
    approve(args.repo, args.task_id, args.reason, args.ttl_seconds)


if __name__ == "__main__":
    main()
