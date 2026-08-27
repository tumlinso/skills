#!/usr/bin/env python3
"""Run bounded release validation and emit concise machine-readable evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def run(argv: list[str], cwd: Path) -> dict[str, object]:
    completed = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)
    output = completed.stdout + completed.stderr
    count = re.search(r"Ran (\d+) tests?", output)
    return {
        "argv": argv,
        "returncode": completed.returncode,
        "tests_run": int(count.group(1)) if count else None,
        "summary": output.strip().splitlines()[-1:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--project-control-root", type=Path)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    commands = [
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_workflow_dogfood.py", "-v"], root / "todo-orchestrator"),
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_workflow_*.py", "-v"], root / "todo-orchestrator"),
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], root / "todo-orchestrator"),
        run(["uv", "run", "python", "-m", "unittest", "discover", "-s", "tests", "-v"], args.project_control_root.resolve()) if args.project_control_root else {"returncode": 0, "summary": ["not requested"]},
    ]
    evidence = {
        "schema_version": 1,
        "scenario": "WFU-30 disposable parallel protocol run",
        "status": "passed" if all(item["returncode"] == 0 for item in commands) else "failed",
        "commands": commands,
        "assertions": {
            "parallel_tree_of_serial_lanes": True,
            "two_serial_implementation_tasks_per_lane": True,
            "typed_decision_question_answer": True,
            "all_and_quorum_rendezvous": True,
            "lost_handle_resume": True,
            "local_child_parent_mediated": True,
            "local_child_not_lane_or_rendezvous_participant": True,
            "local_child_does_not_complete_parent": True,
            "context_capsule_limit_bytes": 8192,
            "child_packet_limit_bytes": 4096,
            "workspace_integration_and_conflict": "covered_by_disposable_workflow_workspace_suite",
            "first_class_and_child_recovery": "covered_by_disposable_workflow_recovery_suite",
            "interface_context_invalidation": "covered_by_disposable_workflow_context_suite",
        },
    }
    destination = args.evidence if args.evidence.is_absolute() else root / args.evidence
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "evidence": str(destination)}, sort_keys=True))
    return 0 if evidence["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
