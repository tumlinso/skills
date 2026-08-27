#!/usr/bin/env python3
"""Installed protocol v2 smoke against one disposable repository."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


EXPECTED = [
    "collect_delegation", "coordinate_task", "delegate_task",
    "finish_task", "inspect_task", "next_task",
]


async def call(session: ClientSession, name: str, arguments: dict[str, object]) -> dict[str, object]:
    result = await session.call_tool(name, arguments)
    if result.structuredContent:
        return dict(result.structuredContent)
    return json.loads(result.content[0].text)


async def exercise(python: str, skills_root: Path, repo: Path, state: Path) -> dict[str, object]:
    parameters = StdioServerParameters(
        command=python,
        args=["-m", "coding_workflow_mcp"],
        env={
            **os.environ,
            "CODING_WORKFLOW_SKILLS_ROOT": str(skills_root),
            "TODO_ORCHESTRATOR_STATE_DIR": str(state),
            "CODEX_THREAD_ID": "wfu31-installed-smoke",
        },
    )
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            initialized = await session.initialize()
            tools = sorted(tool.name for tool in (await session.list_tools()).tools)
            claimed = await call(session, "next_task", {"repo_root": str(repo)})
            handle = str(claimed["workflow_handle"])
            inspected = await call(session, "inspect_task", {"workflow_handle": handle, "kind": "task"})
            synced = await call(session, "coordinate_task", {"workflow_handle": handle, "action": "sync", "payload": {}})
            delegated = await call(session, "delegate_task", {
                "workflow_handle": handle,
                "delegated_objective": "Return immediately when no bounded local adapter is configured",
                "mode": "readonly",
            })
            finished = await call(session, "finish_task", {
                "workflow_handle": handle, "action": "complete", "disposition": "validated",
            })
    return {
        "server": initialized.serverInfo.name,
        "tools": tools,
        "next_status": claimed["status"],
        "inspect_status": inspected["status"],
        "sync_status": synced["status"],
        "delegation_status": delegated["status"],
        "finish_status": finished["status"],
        "protocol_versions": sorted({
            claimed["protocol_version"], inspected["protocol_version"], synced["protocol_version"],
            delegated["protocol_version"], finished["protocol_version"],
        }),
        "secret_fields_present": any(
            marker in json.dumps(value).lower()
            for value in (claimed, inspected, synced, delegated, finished)
            for marker in ("claim_token", "session_token", "worker_token", "approval_token", "traceback")
        ),
    }


def main() -> int:
    skills_root = Path(os.environ["CODING_WORKFLOW_SKILLS_ROOT"]).resolve()
    installed_python = os.environ["CODING_WORKFLOW_INSTALLED_PYTHON"]
    admin = str(Path(installed_python).with_name("coding-workflow-admin"))
    sys.path.insert(0, str(skills_root / "todo-orchestrator"))
    from todo_orchestrator.projections import atomic_write_json
    from todo_orchestrator.service import Service

    with tempfile.TemporaryDirectory(prefix="wfu31-smoke-") as temporary:
        root = Path(temporary)
        repo = root / "repo"
        repo.mkdir()
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
        (repo / "src").mkdir()
        (repo / "src" / "smoke.txt").write_text("smoke\n", encoding="utf-8")
        state = root / "state"
        previous = os.environ.get("TODO_ORCHESTRATOR_STATE_DIR")
        os.environ["TODO_ORCHESTRATOR_STATE_DIR"] = str(state)
        try:
            service, _ = Service.bootstrap(repo, "wfu31-installed-smoke")
            plan = {
                "schema_version": 2,
                "project": {"name": "wfu31-installed-smoke"},
                "tasks": [{
                    "id": "SMOKE", "kind": "validation_task", "title": "Installed smoke",
                    "objective": "Exercise installed protocol", "parallel_policy": "parallel_safe",
                    "scope": {"exclusive_paths": ["src"]},
                }],
                "invariants": [], "decisions": [], "locks": [], "interfaces": [],
                "barriers": [], "resource_classes": [],
            }
            plan_path = repo / "plan.json"
            atomic_write_json(plan_path, plan)
            service.plan_apply(str(plan_path))
            result = asyncio.run(exercise(installed_python, skills_root, repo, state))
            admin_result = subprocess.run(
                [admin, "recover", "--repo", str(repo), "--reason", "installed inspect-only smoke", "--inspect-only"],
                text=True, capture_output=True, check=False,
                env={**os.environ, "TODO_ORCHESTRATOR_STATE_DIR": str(state)},
            )
            result["admin_inspect_only"] = admin_result.returncode == 0 and bool(json.loads(admin_result.stdout))
        finally:
            if previous is None:
                os.environ.pop("TODO_ORCHESTRATOR_STATE_DIR", None)
            else:
                os.environ["TODO_ORCHESTRATOR_STATE_DIR"] = previous
    result["ok"] = (
        result["tools"] == EXPECTED
        and result["protocol_versions"] == [2]
        and result["next_status"] == "claimed"
        and result["inspect_status"] in {"claimed", "context_stale"}
        and result["delegation_status"] == "fallback_authorized"
        and result["finish_status"] == "idle"
        and result["admin_inspect_only"]
        and not result["secret_fields_present"]
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
