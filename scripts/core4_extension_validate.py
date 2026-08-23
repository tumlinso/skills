#!/usr/bin/env python3
"""Focused validation dispatcher for the CORE4 production extension."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
TAIL_BYTES = 4_000


def unittest_file(directory: str, pattern: str) -> list[str]:
    return [PYTHON, "-m", "unittest", "discover", "-s", directory, "-p", pattern, "-v"]


SUITES: dict[str, list[list[str]]] = {
    "baseline": [
        ["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"],
        [PYTHON, "scripts/core4_validate.py", "--metadata-only"],
        [PYTHON, "-m", "unittest", "discover", "-s", "todo-orchestrator/tests", "-v"],
        [PYTHON, "-m", "unittest", "discover", "-s", "cpp-context-compiler/tests", "-v"],
        [PYTHON, "-m", "unittest", "discover", "-s", "cuda/tests", "-v"],
        [PYTHON, "-m", "unittest", "discover", "-s", "local-coding-worker/tests", "-v"],
    ],
    "todo-child": [
        unittest_file("todo-orchestrator/tests", "test_child_execution*.py"),
        unittest_file("todo-orchestrator/tests", "test_v2_recovery_migration_context.py"),
    ],
    "todo-runtime": [
        unittest_file("todo-orchestrator/tests", "test_runtime_facade.py"),
        unittest_file("todo-orchestrator/tests", "test_host_coordination.py"),
        unittest_file("todo-orchestrator/tests", "test_core4_resource_policy.py"),
    ],
    "cuda-evidence": [
        unittest_file("cuda/tests", "test_controller.py"),
        unittest_file("cuda/tests", "test_registry_discovery.py"),
        unittest_file("cuda/tests", "test_performance_facts.py"),
    ],
    "ctxpp-packet": [
        unittest_file("cpp-context-compiler/tests", "test_context_packet.py"),
        unittest_file("cpp-context-compiler/tests", "test_context_packet_economics.py"),
    ],
    "model-cache": [unittest_file("local-coding-worker/tests", "test_model_cache.py")],
    "model-service": [
        unittest_file("local-coding-worker/tests", "test_service.py"),
        unittest_file("local-coding-worker/tests", "test_llama_cpp_server.py"),
    ],
    "qwen-harness": [
        unittest_file("local-coding-worker/tests", "test_harnesses.py"),
        unittest_file("local-coding-worker/tests", "test_telemetry.py"),
    ],
    "worker-readonly-software": [
        unittest_file("local-coding-worker/tests", "test_read_only_mvp.py"),
        unittest_file("local-coding-worker/tests", "test_core4_integration.py"),
    ],
    "worker-writable-software": [
        unittest_file("local-coding-worker/tests", "test_writable_work.py"),
        unittest_file("todo-orchestrator/tests", "test_child_execution_integration.py"),
    ],
    "cuda-integration": [
        unittest_file("cuda/tests", "test_core4_interlock.py"),
        unittest_file("local-coding-worker/tests", "test_core4_integration.py"),
    ],
    "software-ready": [
        [PYTHON, "-m", "unittest", "discover", "-s", "todo-orchestrator/tests", "-v"],
        [PYTHON, "-m", "unittest", "discover", "-s", "cpp-context-compiler/tests", "-v"],
        [PYTHON, "-m", "unittest", "discover", "-s", "cuda/tests", "-v"],
        [PYTHON, "-m", "unittest", "discover", "-s", "local-coding-worker/tests", "-v"],
    ],
    "cache-inspect": [
        [PYTHON, "local-coding-worker/scripts/local_worker.py", "model-cache", "inspect", "--json"],
    ],
    "host-service": [
        [PYTHON, "local-coding-worker/scripts/local_worker.py", "host-check", "--scenario", "service", "--json"],
    ],
    "host-readonly": [
        [PYTHON, "local-coding-worker/scripts/local_worker.py", "host-check", "--scenario", "readonly", "--json"],
    ],
    "host-writable": [
        [PYTHON, "local-coding-worker/scripts/local_worker.py", "host-check", "--scenario", "writable", "--json"],
    ],
    "focused-comparison": [
        [PYTHON, "local-coding-worker/scripts/local_worker.py", "evaluate", "--phase", "focused", "--json"],
    ],
    "production-policy": [
        [PYTHON, "local-coding-worker/scripts/local_worker.py", "policy", "validate", "--json"],
    ],
    "meaningful-eval": [
        [PYTHON, "local-coding-worker/scripts/local_worker.py", "evaluate", "--phase", "meaningful", "--json"],
    ],
    "full": [
        [PYTHON, "-m", "unittest", "discover", "-s", "todo-orchestrator/tests", "-v"],
        [PYTHON, "-m", "unittest", "discover", "-s", "cpp-context-compiler/tests", "-v"],
        [PYTHON, "-m", "unittest", "discover", "-s", "cuda/tests", "-v"],
        [PYTHON, "-m", "unittest", "discover", "-s", "local-coding-worker/tests", "-v"],
    ],
    "cleanup-preflight": [
        [PYTHON, "local-coding-worker/scripts/local_worker.py", "release-check", "--phase", "cleanup", "--json"],
    ],
    "release": [
        [PYTHON, "local-coding-worker/scripts/local_worker.py", "release-check", "--phase", "release", "--json"],
    ],
    "handoff": [
        [PYTHON, "local-coding-worker/scripts/local_worker.py", "release-check", "--phase", "handoff", "--json"],
    ],
}


def git_common_dir() -> Path:
    value = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    path = Path(value)
    return path if path.is_absolute() else (ROOT / path).resolve()


def bounded_tail(value: str) -> str:
    encoded = value.encode("utf-8", errors="replace")
    return encoded[-TAIL_BYTES:].decode("utf-8", errors="replace")


def run_section(section: str) -> dict[str, Any]:
    common = git_common_dir()
    evidence_dir = common / "core4-production-extension" / "evidence"
    raw_dir = common / "core4-production-extension" / "raw" / section
    evidence_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    results: list[dict[str, Any]] = []
    for index, argv in enumerate(SUITES[section], start=1):
        started = time.monotonic()
        process = subprocess.run(
            argv,
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        duration = round(time.monotonic() - started, 3)
        stdout_path = raw_dir / f"{index:02d}.stdout.log"
        stderr_path = raw_dir / f"{index:02d}.stderr.log"
        stdout_path.write_text(process.stdout, encoding="utf-8")
        stderr_path.write_text(process.stderr, encoding="utf-8")
        results.append(
            {
                "command": argv,
                "duration_seconds": duration,
                "exit_code": process.returncode,
                "stdout_tail": bounded_tail(process.stdout),
                "stderr_tail": bounded_tail(process.stderr),
                "raw_stdout": str(stdout_path),
                "raw_stderr": str(stderr_path),
            }
        )
        if process.returncode != 0:
            break
    report = {
        "format": "CORE4-EXTENSION-EVIDENCE/1",
        "section": section,
        "ok": len(results) == len(SUITES[section]) and all(item["exit_code"] == 0 for item in results),
        "commands_required": len(SUITES[section]),
        "commands_run": len(results),
        "results": results,
    }
    output = evidence_dir / f"{section}.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["evidence_path"] = str(output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--section", required=True, choices=sorted(SUITES))
    args = parser.parse_args()
    report = run_section(args.section)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
