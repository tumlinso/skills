#!/usr/bin/env python3
"""Disposable installed-MCP smoke for two concurrent real read-only workers."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


TOOLS = {
    "next_task", "inspect_task", "coordinate_task", "delegate_task",
    "collect_delegation", "finish_task",
}


def command(argv: list[str], cwd: Path) -> dict:
    process = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False)
    if process.returncode:
        raise RuntimeError((process.stderr or process.stdout)[-1000:])
    value = json.loads(process.stdout)
    return value.get("data", value) if isinstance(value, dict) else value


def prepare_fixture(skills: Path, root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src/alpha.cpp").write_text("int alpha() { return 11; }\n", encoding="utf-8")
    (root / "src/beta.cpp").write_text("int beta() { return 13; }\n", encoding="utf-8")
    (root / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.18)\nproject(cwm_smoke LANGUAGES CXX)\n"
        "add_library(cwm_smoke STATIC src/alpha.cpp src/beta.cpp)\n",
        encoding="utf-8",
    )
    (root / ".gitignore").write_text("build/\n.ctxpp/\n.todo-orchestrator/runtime/\n", encoding="utf-8")
    shutil.copy2(skills / "cpp-context-compiler/assets/default.ctxpp.toml", root / ".ctxpp.toml")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "coding-workflow@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Coding Workflow Smoke"], cwd=root, check=True)
    subprocess.run([
        "cmake", "-S", str(root), "-B", str(root / "build"),
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
    ], check=True, stdout=subprocess.DEVNULL)
    (root / "compile_commands.json").symlink_to("build/compile_commands.json")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "disposable semantic fixture"], cwd=root, check=True)
    plan = {
        "schema_version": 2,
        "project": {"name": "Coding Workflow Two Worker Smoke"},
        "tasks": [
            {
                "id": "SMOKE-A", "kind": "workstream", "title": "Review alpha",
                "objective": "Review alpha in src/alpha.cpp and summarize its exact return behavior.",
                "priority": 100, "parallel_policy": "parallel_safe",
                "scope": {"exclusive_paths": ["src/alpha.cpp"]},
                "gates": [{"id": "SMOKE-A-G", "type": "command",
                           "argv": [sys.executable, "-c", "assert True"], "required": True}],
            },
            {
                "id": "SMOKE-B", "kind": "workstream", "title": "Review beta",
                "objective": "Review beta in src/beta.cpp and summarize its exact return behavior.",
                "priority": 100, "parallel_policy": "parallel_safe",
                "scope": {"exclusive_paths": ["src/beta.cpp"]},
                "gates": [{"id": "SMOKE-B-G", "type": "command",
                           "argv": [sys.executable, "-c", "assert True"], "required": True}],
            },
        ],
    }
    plan_path = root / ".git/smoke-plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    todo = skills / "todo-orchestrator/scripts/todo.py"
    command([sys.executable, str(todo), "bootstrap", "--repo-root", str(root),
             "--name", "Coding Workflow Two Worker Smoke", "--json"], root)
    command([sys.executable, str(todo), "plan", "validate", "--repo-root", str(root),
             "--file", str(plan_path), "--json"], root)
    command([sys.executable, str(todo), "plan", "apply", "--repo-root", str(root),
             "--file", str(plan_path), "--json"], root)


def tool_value(result) -> dict:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured
    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if isinstance(text, str):
            value = json.loads(text)
            if isinstance(value, dict):
                return value
    raise RuntimeError("MCP tool did not return an object")


async def smoke(skills: Path, fixture: Path, state: Path, timeout: float) -> dict:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "coding_workflow_mcp"],
        env={**os.environ, "CODING_WORKFLOW_SKILLS_ROOT": str(skills),
             "XDG_STATE_HOME": str(state)},
    )
    handles: list[str] = []
    delegations: list[str] = []
    terminals: list[dict] = []
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            initialized = await session.initialize()
            discovered = {tool.name for tool in (await session.list_tools()).tools}
            if discovered != TOOLS:
                raise RuntimeError(f"unexpected MCP surface: {sorted(discovered)}")
            for task_id in ("SMOKE-A", "SMOKE-B"):
                claimed = tool_value(await session.call_tool(
                    "next_task", {"repo_root": str(fixture), "task_id": task_id},
                ))
                if claimed.get("status") != "claimed":
                    raise RuntimeError(f"claim failed for {task_id}: {claimed.get('status')}")
                handles.append(str(claimed["workflow_handle"]))
            launched = await asyncio.gather(*[
                session.call_tool("delegate_task", {
                    "workflow_handle": handle, "mode": "readonly",
                    "target": "Perform the bounded source review only.",
                }) for handle in handles
            ])
            launch_values = [tool_value(item) for item in launched]
            if any(item.get("status") != "delegated" for item in launch_values):
                for handle in handles:
                    await session.call_tool("finish_task", {
                        "workflow_handle": handle, "action": "release", "disposition": "failed",
                        "reason": "disposable live smoke lacked two admitted local slots",
                    })
                return {"ok": False, "phase": "admission",
                        "statuses": [item.get("status") for item in launch_values]}
            delegations = [str(item["delegation_handle"]) for item in launch_values]
            deadline = time.monotonic() + timeout
            pending = dict.fromkeys(delegations)
            while pending and time.monotonic() < deadline:
                await asyncio.sleep(5)
                for handle in list(pending):
                    value = tool_value(await session.call_tool(
                        "collect_delegation", {"delegation_handle": handle},
                    ))
                    if value.get("status") != "running":
                        terminals.append(value)
                        pending.pop(handle)
            if pending:
                raise RuntimeError("two-worker smoke timed out")
            for handle in handles:
                await session.call_tool("finish_task", {
                    "workflow_handle": handle, "action": "release", "disposition": "validated",
                    "reason": "disposable two-worker smoke completed",
                })
            return {"ok": True, "server": initialized.serverInfo.name,
                    "delegated": len(delegations),
                    "terminal_statuses": [item.get("status") for item in terminals]}


def model_evidence(fixture: Path) -> dict:
    records = []
    for path in sorted((fixture / ".git/local-coding-worker/executions").glob("*/worker-result.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        artifacts = value.get("artifacts") if isinstance(value.get("artifacts"), list) else []
        harness = next((item for item in artifacts if isinstance(item, dict)
                        and item.get("kind") == "harness-summary"), None)
        records.append({"backend_calls": (value.get("telemetry") or {}).get("backend_calls"),
                        "status": value.get("status"), "harness": harness})
    harnesses = [item["harness"] for item in records if isinstance(item.get("harness"), dict)]
    return {
        "worker_results": len(records),
        "model_executions": len(harnesses),
        "unique_slots": len({item.get("slot_id") for item in harnesses if item.get("slot_id")}),
        "unique_servers": len({item.get("server_pid") for item in harnesses if item.get("server_pid")}),
        "backend_calls": [item.get("backend_calls") for item in records],
        "worker_statuses": [item.get("status") for item in records],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skills-root", default=os.environ.get("CODING_WORKFLOW_SKILLS_ROOT", "."))
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--evidence")
    args = parser.parse_args()
    skills = Path(args.skills_root).resolve()
    with tempfile.TemporaryDirectory(prefix="coding-workflow-two-worker-") as temporary:
        root = Path(temporary)
        fixture = root / "fixture"
        fixture.mkdir()
        prepare_fixture(skills, fixture)
        result = asyncio.run(smoke(skills, fixture, root / "state", args.timeout))
        evidence = {**result, "model": model_evidence(fixture)}
    evidence["ok"] = bool(
        evidence.get("ok") and evidence["model"]["model_executions"] == 2
        and evidence["model"]["unique_slots"] == 2
        and evidence["model"]["unique_servers"] == 2
        and evidence["model"]["backend_calls"] == [1, 1]
    )
    destination = Path(args.evidence).resolve() if args.evidence else None
    if destination:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0 if evidence["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
