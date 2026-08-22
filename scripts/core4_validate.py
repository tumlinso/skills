#!/usr/bin/env python3
"""One dependency-free CORE4 compatibility and software-ready validator."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "core4-tests/software-ready/report.json"
SKILLS = ("todo-orchestrator", "cpp-context-compiler", "cuda", "local-coding-worker")
SUITES = {
    "todo-orchestrator": [sys.executable, "-m", "unittest", "discover", "-s", "todo-orchestrator/tests", "-v"],
    "cpp-context-compiler": [sys.executable, "-m", "unittest", "discover", "-s", "cpp-context-compiler/tests", "-v"],
    "cuda": [sys.executable, "-m", "unittest", "discover", "-s", "cuda/tests", "-v"],
    "local-coding-worker": [sys.executable, "-m", "unittest", "discover", "-s", "local-coding-worker/tests", "-v"],
}
PUBLIC_HELP = {
    "todo-orchestrator": ([sys.executable, "todo-orchestrator/scripts/todo.py", "--help"], [
        "checkpoint", "barrier", "interface", "decision", "lock", "resource", "gate", "guard",
        "audit", "reconcile", "recover", "exec", "bootstrap", "init", "status", "doctor",
        "export", "cleanup", "migrate", "plan", "continue", "claim", "ready", "explain",
        "context", "changes", "pulse", "release", "block", "handoff", "complete",
    ]),
    "cpp-context-compiler": (["cpp-context-compiler/scripts/ctxpp", "--help"], [
        "init", "doctor", "status", "scan", "where", "route", "slice", "view", "explain",
        "expand", "audit", "plan", "shard", "apply", "verify", "lint",
    ]),
    "cuda": ([sys.executable, "cuda/scripts/cuda_controller.py", "--help"], [
        "inspect", "background", "run", "evidence", "guide",
    ]),
}


class ValidationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(argv, cwd=ROOT, env=environment, text=True, capture_output=True, check=False)


def _frontmatter(skill: str) -> dict[str, str]:
    content = (ROOT / skill / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        raise ValidationError(f"{skill}/SKILL.md has invalid frontmatter")
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip().strip('"')
    if values.get("name") != skill or not values.get("description"):
        raise ValidationError(f"{skill}/SKILL.md requires matching name and a description")
    if set(values) != {"name", "description"}:
        raise ValidationError(f"{skill}/SKILL.md frontmatter must contain only name and description")
    if len(values["description"]) > 1024 or "<" in values["description"] or ">" in values["description"]:
        raise ValidationError(f"{skill}/SKILL.md description is invalid")
    line_limit, byte_limit = ((40, 2400) if skill == "local-coding-worker" else (90, 4500))
    if len(content.splitlines()) > line_limit or len(content.encode()) > byte_limit:
        raise ValidationError(f"{skill}/SKILL.md exceeds its compact surface budget")
    return {"lines": str(len(content.splitlines())), "bytes": str(len(content.encode()))}


def _agent_metadata(skill: str) -> dict[str, object]:
    text = (ROOT / skill / "agents/openai.yaml").read_text(encoding="utf-8")
    if not text.startswith("interface:\n"):
        raise ValidationError(f"{skill}/agents/openai.yaml must use the interface mapping")
    values = dict(re.findall(r'^  (display_name|short_description|default_prompt): "([^"]+)"$', text, re.MULTILINE))
    if set(values) != {"display_name", "short_description", "default_prompt"}:
        raise ValidationError(f"{skill}/agents/openai.yaml is missing quoted interface fields")
    if not 25 <= len(values["short_description"]) <= 64:
        raise ValidationError(f"{skill} short_description must contain 25-64 characters")
    if f"${skill}" not in values["default_prompt"]:
        raise ValidationError(f"{skill} default_prompt must explicitly name ${skill}")
    if "policy:\n  allow_implicit_invocation: true\n" not in text:
        raise ValidationError(f"{skill} must remain implicitly invocable")
    return {"short_description_chars": len(values["short_description"])}


def _root_contract() -> dict[str, object]:
    guidance = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    lowered = guidance.lower()
    if "markdown is canonical" in lowered or "markdown canonical" in lowered:
        raise ValidationError("AGENTS.md must not call Markdown canonical")
    for skill in SKILLS:
        if f"`{skill}`" not in guidance:
            raise ValidationError(f"AGENTS.md does not route {skill}")
    if "active todo parent claim" not in guidance:
        raise ValidationError("AGENTS.md must guard local worker use with todo parent authority")
    ignore = set((ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())
    required = {"__pycache__/", "*.pyc", ".pytest_cache/", ".ctxpp/", ".todo-orchestrator/runtime/"}
    if not required.issubset(ignore):
        raise ValidationError(f".gitignore is missing entries: {sorted(required - ignore)}")
    suspicious = [line for line in ignore if any(token in line.lower() for token in ("*.gguf", "*.safetensors", "*.bin", "models/"))]
    if suspicious:
        raise ValidationError("model weights must live outside the repository, not behind broad ignore globs")
    return {"required_ignore_entries": sorted(required)}


def _frozen_compatibility() -> dict[str, object]:
    contract = json.loads((ROOT / "contracts/core4-compatibility-v1.json").read_text(encoding="utf-8"))
    checked = 0
    for skill, record in contract["skills"].items():
        for group in ("fixture_hashes", "identity_hashes"):
            for relative, expected in record.get(group, {}).items():
                if relative == "SKILL.md" or (skill == "cuda" and relative == "assets/cuda-markdown-manifest.json"):
                    continue
                target = ROOT / skill / relative if not relative.startswith("core4-tests/") else ROOT / relative
                if _sha256(target) != expected:
                    raise ValidationError(f"frozen compatibility artifact changed: {target.relative_to(ROOT)}")
                checked += 1
    help_results = {}
    for name, (argv, commands) in PUBLIC_HELP.items():
        process = _run(argv)
        if process.returncode != 0:
            raise ValidationError(f"{name} public help failed")
        output = process.stdout + process.stderr
        missing = [command for command in commands if command not in output]
        if missing:
            raise ValidationError(f"{name} public commands disappeared: {missing}")
        help_results[name] = {"commands_preserved": len(commands)}
    return {"frozen_hashes_checked": checked, "public_help": help_results}


def _cross_skill_boundaries() -> dict[str, object]:
    violations = []
    for source in (ROOT / "local-coding-worker").rglob("*.py"):
        if "tests" in source.parts:
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            if module and module.startswith("todo_orchestrator") and module != "todo_orchestrator.runtime":
                violations.append(f"{source.relative_to(ROOT)}:{module}")
            if module and (module.startswith("cuda") or module.startswith("ctxpp")):
                violations.append(f"{source.relative_to(ROOT)}:{module}")
    if violations:
        raise ValidationError(f"new local-worker flow bypasses supported facades: {violations}")
    legacy = ROOT / "cuda/scripts/cuda_controller.py"
    tree = ast.parse(legacy.read_text(encoding="utf-8"), filename=str(legacy))
    legacy_modules = sorted({
        node.module for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("todo_orchestrator.")
    })
    allowed_legacy = {
        "todo_orchestrator.background.artifacts", "todo_orchestrator.background.host",
        "todo_orchestrator.background.resources", "todo_orchestrator.background.store",
        "todo_orchestrator.background.wake", "todo_orchestrator.config",
    }
    if set(legacy_modules) != allowed_legacy:
        raise ValidationError("legacy CUDA compatibility imports changed; migrate them only with an explicit facade contract")
    return {
        "supported_new_import": "todo_orchestrator.runtime",
        "legacy_cuda_compatibility_modules": legacy_modules,
    }


def metadata_validation() -> dict[str, object]:
    return {
        "root": _root_contract(),
        "skills": {skill: {"surface": _frontmatter(skill), "agent": _agent_metadata(skill)} for skill in SKILLS},
        "compatibility": _frozen_compatibility(),
        "cross_skill_boundaries": _cross_skill_boundaries(),
    }


def _suite(name: str, argv: list[str]) -> dict[str, object]:
    started = time.perf_counter()
    process = _run(argv)
    output = process.stdout + "\n" + process.stderr
    match = re.search(r"Ran (\d+) tests?", output)
    result: dict[str, object] = {
        "command": argv,
        "returncode": process.returncode,
        "tests_run": int(match.group(1)) if match else None,
        "duration_seconds": round(time.perf_counter() - started, 3),
    }
    if process.returncode != 0:
        result["failure_tail"] = output[-8000:]
    return result


def _json_command(argv: list[str]) -> object:
    process = _run(argv)
    if process.returncode != 0:
        raise ValidationError(f"JSON command failed: {argv}")
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise ValidationError(f"JSON command returned invalid output: {argv}") from error
    if isinstance(value, dict) and value.get("ok") is True:
        return value.get("data")
    raise ValidationError(f"JSON command returned an error envelope: {argv}")


def _release_validation() -> dict[str, object]:
    profile_path = ROOT / "local-coding-worker/config/production-profile.toml"
    profile = tomllib.loads(profile_path.read_text(encoding="utf-8"))
    storage = profile.get("storage", {})
    deployment = profile.get("deployment_policy", {})
    for field in ("canonical_root", "staging_root"):
        path = Path(str(storage.get(field, "")))
        if not path.is_absolute() or path == ROOT or ROOT in path.parents:
            raise ValidationError(f"production profile {field} must be an absolute external path")
    required_disabled = ("real_local_enabled", "reviewer_enabled", "double_solve_enabled")
    if any(deployment.get(field) is not False for field in required_disabled):
        raise ValidationError("unmeasured local deployment features must remain disabled")
    if int(deployment.get("hot_idle_seconds", -1)) != 0 or int(deployment.get("max_real_workers", -1)) != 0:
        raise ValidationError("unpromoted local inference must not retain a hot model or workers")
    if deployment.get("needs_codex_is_success") is not True:
        raise ValidationError("NEEDS_CODEX must remain a successful hand-back")

    policy_report = json.loads((ROOT / "local-coding-worker/evals/results/policy-report.json").read_text(encoding="utf-8"))
    if policy_report.get("format") != "CORE4-POLICY-REPORT/1":
        raise ValidationError("policy report format is invalid")
    if policy_report.get("deployment", {}).get("selected_candidate") is not None:
        raise ValidationError("policy report must not invent a selected candidate")
    if policy_report.get("policy", {}).get("real_local_enabled") is not False:
        raise ValidationError("policy report contradicts the unpromoted host result")

    model_files = [str(path.relative_to(ROOT)) for suffix in ("*.gguf", "*.safetensors")
                   for path in ROOT.rglob(suffix)]
    if model_files:
        raise ValidationError(f"model weights are present in the repository: {model_files[:8]}")
    staging_root = Path(str(storage["staging_root"]))
    staged_entries = sorted(item.name for item in staging_root.iterdir()) if staging_root.is_dir() else []
    if staged_entries:
        raise ValidationError(f"SSD staging was not cleaned: {staged_entries[:8]}")

    todo = [sys.executable, "todo-orchestrator/scripts/todo.py"]
    doctor = _json_command([*todo, "doctor", "--repo-root", str(ROOT), "--json"])
    if not isinstance(doctor, dict) or doctor.get("database", {}).get("integrity") != "ok":
        raise ValidationError("todo database integrity check failed")
    if doctor.get("database", {}).get("foreign_key_errors"):
        raise ValidationError("todo database has foreign-key errors")
    active_claims = doctor.get("audit", {}).get("active_claims", [])
    unexpected_claims = [item for item in active_claims
                         if not isinstance(item, dict) or item.get("task_id") != "CORE4-19" or item.get("state") != "active"]
    if unexpected_claims or len(active_claims) > 1:
        raise ValidationError(f"unexpected live todo claims: {unexpected_claims or active_claims}")
    resources = _json_command([*todo, "resource", "list", "--repo-root", str(ROOT), "--json"])
    if not isinstance(resources, list) or any(int(item.get("active", 0)) for item in resources if isinstance(item, dict)):
        raise ValidationError("todo resource leases remain active")

    project = json.loads((ROOT / ".todo-orchestrator/project.json").read_text(encoding="utf-8"))
    snapshot = json.loads((ROOT / ".todo-orchestrator/state.snapshot.json").read_text(encoding="utf-8"))
    if snapshot.get("project", {}).get("project_uuid") != project.get("project_uuid"):
        raise ValidationError("todo snapshot project identity does not match project.json")
    status_text = (ROOT / "todo-status.md").read_text(encoding="utf-8")
    if f"Project revision: `{snapshot.get('project_revision')}`" not in status_text:
        raise ValidationError("todo-status.md does not project the current snapshot revision")
    return {
        "host_profile": {
            "canonical_root": str(storage["canonical_root"]),
            "staging_root": str(staging_root),
            "real_local_enabled": False,
            "staging_clean": True,
        },
        "policy_report": {"format": policy_report["format"], "selected_candidate": None},
        "todo": {"database_integrity": "ok", "active_claims": len(active_claims),
                 "active_resource_leases": 0, "project_revision": snapshot.get("project_revision")},
        "model_weights_in_repository": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--software-ready", action="store_true")
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if sum((args.software_ready, args.metadata_only, args.full)) != 1:
        parser.error("choose exactly one of --software-ready, --metadata-only, or --full")
    if args.output is not None and not args.full:
        parser.error("--output is supported only with --full")
    artifact = ARTIFACT
    if args.full:
        output_dir = (args.output or Path("core4-tests/release")).resolve()
        artifact = output_dir / "report.json"
    report: dict[str, Any] = {
        "format": "CORE4-RELEASE/1" if args.full else "CORE4-SOFTWARE-READY/1",
        "schema_version": 1,
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip(),
        "metadata": None,
        "suites": {},
        "software_ready": False,
        "release": None,
        "external_assets_used": False,
    }
    try:
        report["metadata"] = metadata_validation()
        if args.software_ready or args.full:
            report["suites"] = {name: _suite(name, argv) for name, argv in SUITES.items()}
            failures = [name for name, result in report["suites"].items() if result["returncode"] != 0]
            if failures:
                raise ValidationError(f"software-ready suites failed: {failures}")
        report["software_ready"] = args.software_ready or args.full
        if args.full:
            report["release"] = _release_validation()
        report["ok"] = True
    except (OSError, ValueError, SyntaxError, ValidationError) as error:
        report["ok"] = False
        report["error"] = str(error)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
