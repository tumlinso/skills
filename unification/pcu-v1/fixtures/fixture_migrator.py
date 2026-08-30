#!/usr/bin/env python3
"""Fixture-only reversible migrator used by PCU harness tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


OLD = """<!-- coding-workflow:start -->
old fixture guidance
<!-- coding-workflow:end -->"""
NEW = """<!-- project-control:start -->
new fixture guidance
<!-- project-control:end -->"""


def transform(mode: str) -> None:
    agents = Path("AGENTS.md")
    project = Path(".todo-orchestrator/project.json")
    text = agents.read_text(encoding="utf-8")
    config = json.loads(project.read_text(encoding="utf-8"))
    if mode == "apply":
        text = text.replace(OLD, NEW)
        config["configuration"]["workflow_front_door"] = "project-control"
    elif mode == "remove":
        text = text.replace(NEW, OLD)
        config["configuration"]["workflow_front_door"] = "coding-workflow"
    elif mode != "dry-run":
        raise ValueError(mode)
    if mode != "dry-run":
        agents.write_text(text, encoding="utf-8")
        project.write_text(json.dumps(config, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("dry-run", "apply", "remove"))
    args = parser.parse_args()
    transform(args.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
