#!/usr/bin/env python3
"""Run the V100 atlas campaign through the supported foreground controller.

This process is only a coordinator. Every CUDA command (including correctness,
sanitizer, timing, and profiler invocations) is started by cuda_controller.py.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import platform
import re
import sqlite3
import shutil
import statistics
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
sys.path.insert(0, str(ROOT / "scripts"))
import atlas_report
MATRIX_PATH = ROOT / "benchmarks" / "suite_matrix.json"
CONTROLLER = Path("/home/tumlinson/.agents/skills/cuda/scripts/cuda_controller.py")
CUDA_ROOT = Path("/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/cuda/12.9")
NVCC = CUDA_ROOT / "bin" / "nvcc"
SANITIZER = CUDA_ROOT / "compute-sanitizer" / "compute-sanitizer"
NSYS_BIN = Path("/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/profilers/12.9/Nsight_Systems_2025.3/bin")
NCU_BIN = Path("/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/profilers/12.9/Nsight_Compute")
BUILD = ROOT / "build"
RESULT_SCHEMA = ROOT / "experiments" / "result.schema.json"
RESTRICTED = {f"E{i:02d}" for i in (4, 27, 28, 29, 30)}
ALLOWED_STATUSES = {"NOT_RUN", "CPU_ONLY", "COMPILED_ONLY", "GPU_RUN", "REJECTED", "INCONCLUSIVE"}
CASE_STATUSES = ALLOWED_STATUSES


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes()) if path.is_file() else "missing"


def git(*args: str) -> str:
    p = subprocess.run(["git", "-C", str(ROOT), *args], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return p.stdout.strip() if p.returncode == 0 else ""


def source_identity() -> dict[str, str]:
    paths = git("ls-files", "-co", "--exclude-standard").splitlines()
    h = hashlib.sha256()
    selected: dict[str, str] = {}
    generated = ("build/", ".todo-orchestrator/", "benchmark_runs/", "todos/", "__pycache__/")
    for rel in sorted(p for p in paths if p and p not in {"todos.md", "todo-status.md"}
                      and not p.startswith(generated)):
        path = ROOT / rel
        if path.is_file():
            value = digest_file(path)
            selected[rel] = value
            h.update(rel.encode()); h.update(b"\0"); h.update(value.encode()); h.update(b"\n")
    return {"tree_sha256": h.hexdigest(), "files_sha256": digest_bytes(json.dumps(selected, sort_keys=True).encode())}


def command_output(argv: list[str], timeout: int = 8) -> dict[str, Any]:
    try:
        p = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout, check=False)
        return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"returncode": None, "stdout": "", "stderr": str(exc)}


def machine_identity() -> dict[str, Any]:
    smi = command_output(["nvidia-smi", "--query-gpu=index,uuid,name,compute_cap,driver_version,pci.bus_id,vbios_version",
                          "--format=csv,noheader"])
    topo = command_output(["nvidia-smi", "topo", "-m"])
    return {
        "host": platform.node(), "system": platform.platform(),
        "gpu_inventory": smi, "topology": topo,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
    }


def tool_versions() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, path in (("nvcc", NVCC), ("compute_sanitizer", SANITIZER),
                      ("nsys", NSYS_BIN / "nsys"), ("ncu", NCU_BIN / "ncu")):
        out[key] = {"path": str(path), **command_output([str(path), "--version"], timeout=12)}
    return out


def controller_runtime_identity() -> dict[str, Any]:
    skill = CONTROLLER.parent.parent
    tracked = [CONTROLLER, skill / "cuda_toolchain.py", skill / "scripts" / "profile_nsys.sh",
               skill / "scripts" / "profile_ncu.sh", skill / "scripts" / "debug_compute_sanitizer.sh",
               skill / "scripts" / "with_benchmark_mutex.sh", skill / "SKILL.md"]
    return {str(path): {"sha256": digest_file(path), "exists": path.is_file()} for path in tracked}


def load_matrix() -> dict[str, Any]:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    if matrix.get("schema_version") != 1 or not isinstance(matrix.get("experiments"), dict):
        raise ValueError("suite_matrix.json must contain schema_version 1 and experiments")
    return matrix


def validate_ids(ids: list[str], matrix: dict[str, Any]) -> None:
    all_ids = {f"E{i:02d}" for i in range(40)}
    unknown = sorted(set(ids) - all_ids)
    if unknown:
        raise ValueError("unknown experiment ID(s): " + ", ".join(unknown))
    absent = sorted(e for e in ids if e not in matrix["experiments"] and e not in RESTRICTED)
    if absent:
        raise ValueError("matrix missing experiment(s): " + ", ".join(absent))


def percentile95(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, math.ceil(0.95 * len(s)) - 1)]


def summarize_case(case: dict[str, Any]) -> None:
    samples = case.get("samples")
    if not isinstance(samples, dict):
        return
    metrics = case.setdefault("metrics", {})
    for name, raw in samples.items():
        if isinstance(raw, list) and raw and all(isinstance(v, (int, float)) for v in raw):
            metrics.setdefault(f"{name}_median", statistics.median(raw))
            metrics.setdefault(f"{name}_p95", percentile95(raw))


def normalize_cases(payload: dict[str, Any], experiment: str) -> tuple[list[dict[str, Any]], bool]:
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("benchmark JSON must include a nonempty cases array")
    valid = True
    normalized = []
    for raw in cases:
        if not isinstance(raw, dict) or raw.get("experiment") != experiment:
            raise ValueError("benchmark returned a malformed or mismatched case")
        item = dict(raw)
        if item.get("status") not in CASE_STATUSES:
            raise ValueError(f"benchmark returned unsupported status: {item.get('status')!r}")
        summarize_case(item)
        check = item.get("checks", {})
        # NOT_RUN/INCONCLUSIVE capability cases are not failed correctness runs.
        is_executed = item.get("status") in {"GPU_RUN", "CPU_ONLY", "COMPILED_ONLY"}
        valid = valid and (not is_executed or check.get("valid") is True)
        normalized.append(item)
    return normalized, valid


def disposition(experiment: str, status: str, *, cases: list[dict[str, Any]] | None = None,
                limitations: list[str] | None = None, hardware: dict[str, Any] | None = None,
                software: dict[str, Any] | None = None, protocol: dict[str, Any] | None = None,
                raw_artifacts: list[str] | None = None) -> dict[str, Any]:
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"invalid result status {status!r}")
    cases = cases or []
    executed_cases = [c for c in cases if c.get("status") in {"GPU_RUN", "CPU_ONLY", "COMPILED_ONLY"}]
    executed = bool(executed_cases)
    passed = all(c.get("checks", {}).get("valid", False) for c in executed_cases)
    if not executed:
        correctness_text = "no executed correctness result"
    elif passed:
        correctness_text = "correctness passed"
    else:
        correctness_text = "correctness failed"
    summary = f"{len(cases)} case(s); {correctness_text}"
    return {
        "experiment": experiment, "status": status,
        "hardware": hardware or {}, "software": software or {}, "protocol": protocol or {},
        "samples": cases, "correctness": {"valid": passed if executed else None,
                                             "executed_cases": len(executed_cases)},
        "limitations": limitations or [], "source_hashes": {},
        "date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "result_summary": summary, "raw_artifacts": raw_artifacts or [],
    }


def env_command(argv: list[str], recipe: str) -> list[str]:
    bins = [str(NSYS_BIN), str(NCU_BIN), str(CUDA_ROOT / "bin")]
    current = os.environ.get("PATH", "/usr/bin:/bin")
    return ["/usr/bin/env", f"PATH={os.pathsep.join(bins + [current])}", *argv]


def controller_call(argv: list[str], *, recipe: str, uuids: list[str], timeout: int,
                    binary_paths: list[str], build_argv: list[str] | None = None) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "schema_version": 1, "project_root": str(ROOT),
        "argv": env_command(argv, recipe), "recipe": recipe,
        "resources": {"gpu_uuids": uuids, "gpus": len(uuids),
                      "isolate_pcie_root": False, "isolate_nvlink_domain": False},
        "toolchain": {"root": str(CUDA_ROOT), "require_sanitizer": True},
        "timeout": timeout, "binary_paths": binary_paths,
        "paths": ["benchmarks", "scripts", "CMakeLists.txt"],
    }
    if build_argv:
        spec["benchmark"] = {"build_argv": build_argv}
        spec["build_timeout"] = 1800
    spec_path = None
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump(spec, f); f.write("\n"); spec_path = Path(f.name)
        controller_env = os.environ.copy()
        controller_env["NSYS_BIN"] = str(NSYS_BIN / "nsys")
        controller_env["NCU_BIN"] = str(NCU_BIN / "ncu")
        controller_env["COMPUTE_SANITIZER_BIN"] = str(SANITIZER)
        controller_env["PATH"] = os.pathsep.join([str(NSYS_BIN), str(NCU_BIN),
                                                    str(CUDA_ROOT / "bin"), controller_env.get("PATH", "/usr/bin:/bin")])
        p = subprocess.run([sys.executable, str(CONTROLLER), "run", "--spec", str(spec_path), "--json"],
                           cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env=controller_env, timeout=timeout + 120, check=False)
        try:
            result = json.loads(p.stdout)
        except json.JSONDecodeError as exc:
            return {"ok": False, "controller_returncode": p.returncode,
                    "error": f"controller did not return JSON: {exc}",
                    "stdout": p.stdout[-3000:], "stderr": p.stderr[-3000:]}
        result["controller_returncode"] = p.returncode
        if p.stderr.strip():
            result["controller_stderr"] = p.stderr[-3000:]
        return result
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        if spec_path:
            spec_path.unlink(missing_ok=True)


def read_capture(path_value: Any) -> dict[str, Any] | None:
    if not isinstance(path_value, str) or not Path(path_value).is_file():
        return None
    try:
        return json.loads(Path(path_value).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def gpu_uuids(machine: dict[str, Any]) -> list[str]:
    mapping = gpu_uuid_by_index(machine)
    return [mapping[index] for index in sorted(mapping)]


def gpu_uuid_by_index(machine: dict[str, Any]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    rows = machine.get("gpu_inventory", {}).get("stdout", "").splitlines()
    for row in rows:
        parts = [x.strip() for x in row.split(",")]
        if len(parts) >= 2:
            try:
                mapping[int(parts[0])] = parts[1]
            except ValueError:
                continue
    return mapping


def binary_identity(matrix: dict[str, Any]) -> dict[str, str]:
    targets = {str(v["target"]) for v in matrix["experiments"].values() if v.get("target")}
    targets.update(str(case["target"]) for entry in matrix["experiments"].values()
                   for case in entry.get("cases", []) if case.get("target"))
    return {target: digest_file(BUILD / "bin" / target) for target in sorted(targets)}


def resume_compatible(old_config: dict[str, Any], key: str) -> bool:
    return old_config.get("campaign_key") == key


def dependency_failures(experiment: str, results: dict[str, Any], matrix: dict[str, Any]) -> list[str]:
    entry = matrix["experiments"].get(experiment, {})
    failed = []
    for dependency in entry.get("depends_on", []):
        result = results.get(dependency)
        if result is None:
            continue
        cases = result.get("samples", [])
        bad_case = any(c.get("status") in {"GPU_RUN", "CPU_ONLY", "COMPILED_ONLY"}
                       and c.get("checks", {}).get("valid") is False for c in cases)
        if bad_case or result.get("status") in {"REJECTED", "INCONCLUSIVE"}:
            failed.append(dependency)
    return failed


def capture_problem(outcome: dict[str, Any], capture: dict[str, Any] | None) -> str | None:
    if capture is None:
        if outcome.get("timeout") or outcome.get("timed_out"):
            return "controller run timed out and stdout is unavailable"
        if not outcome.get("ok"):
            return "controller run failed and stdout is unavailable"
        return "controller stdout artifact is missing or is not valid JSON"
    if not isinstance(capture.get("cases"), list) or not capture["cases"]:
        return "benchmark stdout has no machine-readable cases"
    # Retain machine-readable failure cases even when the benchmark/controller
    # returned nonzero. The caller then invalidates the measurement explicitly.
    return None


def profile_failure(status: str, outcome: dict[str, Any], recipe: str) -> tuple[str, str | None]:
    if outcome.get("ok"):
        return status, None
    return "INCONCLUSIVE", f"{recipe} capture failed or was denied: {json.dumps(outcome, sort_keys=True)[:1500]}"


def has_required_profiles(result: dict[str, Any], entry: dict[str, Any], policy: str) -> bool:
    samples = result.get("samples", [])
    if result.get("status") == "NOT_RUN" or (samples and all(c.get("status") == "NOT_RUN" for c in samples)):
        return True
    if not entry.get("nsys_eligible", False):
        return True
    if policy != "focused":
        return False
    profiles = [c.get("profiles", {}) for c in samples]
    nsys_ok = any(p.get("nsys", {}).get("trace_has_gpu_work") is True for p in profiles)
    ncu_ok = (not entry.get("ncu_replay_safe", False) or
              any(p.get("ncu", {}).get("counter_valid") is True for p in profiles))
    return nsys_ok and ncu_ok


def result_complete_for_resume(result: dict[str, Any], entry: dict[str, Any], policy: str) -> bool:
    """Only reuse an executed, correctness-qualified disposition with its requested profiles."""
    if result.get("status") not in {"GPU_RUN", "CPU_ONLY"}:
        return False
    if result.get("correctness", {}).get("valid") is not True:
        return False
    executed = [case for case in result.get("samples", []) if case.get("status") in {"GPU_RUN", "CPU_ONLY"}]
    if any(case.get("checks", {}).get("valid") is not True for case in executed):
        return False
    return has_required_profiles(result, entry, policy)


def full_timing_sample_problem(case: dict[str, Any], minimum: int = 30) -> str | None:
    raw_samples = case.get("samples", {})
    timed = {name: values for name, values in raw_samples.items()
             if isinstance(values, list) and any(token in name.lower() for token in
                                                 ("_ms", "_us", "_s", "latency", "throughput", "gb_per_s", "cycles"))
             and "setup" not in name.lower()}
    if not timed:
        return "no raw timing sample vector is present"
    short = {name: len(values) for name, values in timed.items() if len(values) < minimum}
    if short:
        return f"timing vectors have fewer than {minimum} raw samples: {short}"
    return None


def finalize_native_status(status: str, cases: list[dict[str, Any]]) -> tuple[str, str | None]:
    if status != "GPU_RUN" or any(case.get("status") == "GPU_RUN" for case in cases):
        return status, None
    if cases and all(case.get("status") == "NOT_RUN" for case in cases):
        return "NOT_RUN", "All requested subcases were capability-gated as unsupported."
    return "INCONCLUSIVE", "No supported GPU case completed with a measurement."


def focused_profile_indices(experiment: str, entry: dict[str, Any], cases: list[dict[str, Any]]) -> set[int]:
    explicit = entry.get("profile_case_indices")
    if isinstance(explicit, list):
        selected = {int(index) for index in explicit if isinstance(index, int) and 0 <= index < len(cases)}
        return selected or ({0} if cases else set())
    if experiment == "E39":
        # The checked-in matrix selects a nontrivial size with the highest reuse.
        return {0} if cases else set()
    if experiment == "E11":
        candidates = [(int(c.get("size", c.get("universe", 0))), i)
                      for i, c in enumerate(cases)]
        return {max(candidates)[1]} if candidates else set()
    return {0} if cases else set()


def lease_ordinals(case_spec: dict[str, Any], group: str, leased_count: int) -> tuple[int, int | None]:
    """Validate device/peer ordinals in the exact CUDA_VISIBLE_DEVICES lease order."""
    device = int(case_spec.get("device", 0))
    peer = int(case_spec["peer"]) if "peer" in case_spec else (1 if group == "pair" else None)
    if not 0 <= device < leased_count:
        raise ValueError(f"device ordinal {device} is outside the {leased_count}-GPU lease")
    if peer is not None:
        if group not in {"pair", "all"}:
            raise ValueError(f"peer ordinal {peer} is invalid for resource group {group!r}")
        if not 0 <= peer < leased_count:
            raise ValueError(f"peer ordinal {peer} is outside the {leased_count}-GPU lease")
        if peer == device:
            raise ValueError("peer and source device ordinals must differ")
    return device, peer


def validate_result_records(results: dict[str, Any]) -> None:
    schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
    properties = set(schema["properties"])
    required = set(schema["required"])
    allowed = set(schema["properties"]["status"]["enum"])
    for experiment, result in results.items():
        missing = required - set(result)
        extra = set(result) - properties
        if missing or extra or result.get("status") not in allowed or result.get("experiment") != experiment:
            raise ValueError(f"result {experiment} violates result.schema.json: missing={sorted(missing)}, extra={sorted(extra)}")


def validate_profile_artifacts(recipe: str, outcome: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Validate real report and summary files from the controller's profiler receipt."""
    stdout = outcome.get("stdout_path")
    if not isinstance(stdout, str) or not Path(stdout).is_file():
        return False, {"reason": "controller stdout receipt is missing"}
    run_dir = Path(stdout).parent / recipe / "run"
    summary_path = run_dir / "summary.json"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, {"reason": f"profiler summary is missing or invalid: {exc}"}
    if not isinstance(summary, dict):
        return False, {"reason": "profiler summary must be a JSON object"}
    if recipe == "nsys":
        report = run_dir / "report.nsys-rep"
        sqlite_path = run_dir / "report.sqlite"
        activity_counts, sqlite_problem = nsys_sqlite_activity_counts(sqlite_path)
        gpu_mem_csv = next(iter(sorted(run_dir.glob("stats*gpumemtimesum*.csv"))), None)
        gpu_mem_rows: list[dict[str, str]] = []
        if gpu_mem_csv and gpu_mem_csv.stat().st_size:
            try:
                with gpu_mem_csv.open(newline="", encoding="utf-8") as stream:
                    gpu_mem_rows = [row for row in csv.DictReader(stream) if any(value for value in row.values())]
            except (OSError, csv.Error):
                gpu_mem_rows = []
        gpu_activity_rows = sum(activity_counts.values())
        trace_has_gpu_work = gpu_activity_rows > 0
        valid = (report.is_file() and report.stat().st_size > 0 and trace_has_gpu_work
                 and summary.get("status") in {"ok", "partial", "rerun"})
        evidence = {"report": str(report), "report_bytes": report.stat().st_size if report.exists() else 0,
                    "summary": summary, "gpu_memtimes_csv": str(gpu_mem_csv) if gpu_mem_csv else None,
                    "gpu_memtime_rows": len(gpu_mem_rows), "sqlite_path": str(sqlite_path),
                    "sqlite_activity_counts": activity_counts, "sqlite_activity_rows": gpu_activity_rows,
                    "sqlite_problem": sqlite_problem, "trace_has_gpu_work": trace_has_gpu_work}
    elif recipe == "ncu":
        report = run_dir / "report.ncu-rep"
        raw = run_dir / "raw.csv"
        raw_rows: list[dict[str, str]] = []
        if raw.is_file() and raw.stat().st_size:
            try:
                with raw.open(newline="", encoding="utf-8") as stream:
                    raw_rows = [row for row in csv.DictReader(stream) if any(value for value in row.values())]
            except (OSError, csv.Error):
                raw_rows = []
        valid = (report.is_file() and report.stat().st_size > 0 and raw.is_file()
                 and raw.stat().st_size > 0 and bool(raw_rows) and summary.get("status") in {"ok", "partial", "rerun"}
                 and summary.get("counter_valid") is True)
        evidence = {"report": str(report), "report_bytes": report.stat().st_size if report.exists() else 0,
                    "raw_csv": str(raw), "raw_csv_bytes": raw.stat().st_size if raw.exists() else 0,
                    "raw_csv_rows": len(raw_rows), "summary": summary,
                    "counter_valid": summary.get("counter_valid") is True}
    else:
        return False, {"reason": f"unknown profiler recipe {recipe}"}
    return valid, evidence


def validate_child_correctness(outcome: dict[str, Any], experiment: str) -> tuple[bool, dict[str, Any]]:
    """Require a successful, machine-readable verification child with executed valid cases."""
    capture = read_capture(outcome.get("stdout_path"))
    problem = capture_problem(outcome, capture)
    if problem:
        return False, {"reason": problem}
    try:
        cases, all_valid = normalize_cases(capture, experiment)
    except ValueError as exc:
        return False, {"reason": f"verification child JSON contract failed: {exc}"}
    executed = [case for case in cases if case.get("status") in {"GPU_RUN", "CPU_ONLY", "COMPILED_ONLY"}]
    unsupported_only = bool(cases) and all(case.get("status") == "NOT_RUN" for case in cases)
    def has_unsupported_reason(case: dict[str, Any]) -> bool:
        limitations = case.get("limitations", [])
        if not isinstance(limitations, list):
            limitations = []
        candidates = limitations + [case.get("reason"), case.get("limitation")]
        return any(isinstance(reason, str) and reason.strip() for reason in candidates)
    unsupported_reason_valid = all(case.get("status") != "NOT_RUN" or has_unsupported_reason(case) for case in cases)
    passed = bool(outcome.get("ok")) and unsupported_reason_valid and (
        unsupported_only or (all_valid and bool(executed) and all(
            case.get("checks", {}).get("valid") is True for case in executed)))
    return passed, {"controller_ok": bool(outcome.get("ok")), "executed_cases": len(executed),
                    "case_statuses": [case.get("status") for case in cases],
                    "correctness": [case.get("checks", {}).get("valid") for case in executed],
                    "unsupported_only": unsupported_only,
                    "unsupported_reason_valid": unsupported_reason_valid,
                    "normalized_cases": cases,
                    "reason": None if passed else "verification child had no executed passing oracle case or controller invalidated it"}


def nsys_sqlite_activity_counts(sqlite_path: Path) -> tuple[dict[str, int], str | None]:
    """Count captured GPU execution/copy/fill activity from Nsight's authoritative SQLite export."""
    counts = {"kernels": 0, "memcpy": 0, "memset": 0}
    if not sqlite_path.is_file() or sqlite_path.stat().st_size == 0:
        return counts, "Nsight SQLite report is missing or empty"
    kernel_tables = {"CUPTI_ACTIVITY_KIND_KERNEL", "CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL"}
    memcpy_tables = {"CUPTI_ACTIVITY_KIND_MEMCPY", "CUPTI_ACTIVITY_KIND_MEMCPY2",
                     "CUPTI_ACTIVITY_KIND_CONCURRENT_MEMCPY"}
    memset_tables = {"CUPTI_ACTIVITY_KIND_MEMSET", "CUPTI_ACTIVITY_KIND_MEMSET2",
                     "CUPTI_ACTIVITY_KIND_CONCURRENT_MEMSET"}
    try:
        connection = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
        try:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for category, selected in (("kernels", kernel_tables), ("memcpy", memcpy_tables), ("memset", memset_tables)):
                for table in tables.intersection(selected):
                    counts[category] += int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        finally:
            connection.close()
    except (OSError, sqlite3.Error) as exc:
        return counts, f"Cannot read Nsight SQLite activity tables: {exc}"
    return counts, None


def validate_sanitizer_outcome(outcome: dict[str, Any], tool: str, *, child_valid: bool) -> tuple[bool, dict[str, Any]]:
    """Gate on the selected tool's raw zero-error summary, not advisory crash-classifier status."""
    stdout_path = outcome.get("stdout_path")
    if not isinstance(stdout_path, str) or not Path(stdout_path).is_file():
        return False, {"tool": tool, "reason": "sanitizer stdout receipt is missing"}
    anchor = Path(stdout_path).parent
    summary_path = anchor / "sanitizer" / "run" / "summary.txt"
    raw_path = anchor / "sanitizer" / "run" / "raw.log"
    stdout = Path(stdout_path).read_text(encoding="utf-8", errors="replace")
    summary = summary_path.read_text(encoding="utf-8", errors="replace") if summary_path.is_file() else ""
    raw = raw_path.read_text(encoding="utf-8", errors="replace") if raw_path.is_file() else ""
    # The controller's compute-sanitizer recipe preserves raw.log. Direct
    # racecheck/synccheck baseline invocations expose the raw tool output on stdout.
    raw_source = raw if raw_path.is_file() else stdout
    error_counts: list[int] = []
    race_summaries: list[tuple[int, int, int]] = []
    if tool.lower() == "racecheck":
        race_summaries = [(int(m.group(1)), int(m.group(2)), int(m.group(3))) for m in re.finditer(
            r"RACECHECK SUMMARY:\s*(\d+)\s+hazards? displayed\s*\((\d+) errors?,\s*(\d+) warnings?\)",
            raw_source, re.IGNORECASE)]
        explicit_zero = len(race_summaries) == 1 and race_summaries[0] == (0, 0, 0)
    else:
        error_counts = [int(m.group(1)) for m in re.finditer(r"ERROR SUMMARY:\s*(\d+)\s+errors?", raw_source, re.IGNORECASE)]
        explicit_zero = len(error_counts) == 1 and error_counts[0] == 0
    status_match = re.search(r"^status:\s*(\S+)\s*$", summary, re.IGNORECASE | re.MULTILINE)
    conclusive_match = re.search(r"^conclusive:\s*(\S+)\s*$", summary, re.IGNORECASE | re.MULTILINE)
    diagnostic_lines = [line for line in raw_source.splitlines()
                        if not re.search(r"(?:ERROR SUMMARY:|RACECHECK SUMMARY:)", line, re.IGNORECASE)]
    diagnostic_source = "\n".join(diagnostic_lines)
    warnings = re.findall(r"(?:^|\n)\s*(?:=========\s*)?WARNING\b[^\n]*", diagnostic_source, re.IGNORECASE)
    api_device_errors = re.findall(r"(?:cudaError[A-Za-z0-9_]+|Program hit .*?error|=========\s*(?:Error|Invalid|Race|Uninitialized|Warp|Synccheck)\b[^\n]*)",
                                   diagnostic_source, re.IGNORECASE)
    returncode = outcome.get("returncode")
    passed = bool(outcome.get("ok")) and returncode == 0 and child_valid and explicit_zero and not warnings and not api_device_errors
    evidence = {"tool": tool, "controller_ok": bool(outcome.get("ok")),
                "returncode": returncode, "child_valid": child_valid,
                "error_counts": error_counts, "zero_errors": explicit_zero,
                "racecheck_summaries": race_summaries,
                "warnings": warnings, "api_device_errors": api_device_errors,
                "status": status_match.group(1) if status_match else None,
                "conclusive": conclusive_match.group(1) if conclusive_match else None,
                "summary": str(summary_path) if summary_path.is_file() else None,
                "raw_log": str(raw_path) if raw_path.is_file() else None,
                "reason": None if passed else ("sanitizer raw output lacked exactly one zero-error summary" if not explicit_zero else "sanitizer warning/API/device error, invalid child, or controller failure")}
    return passed, evidence


def child_argv(entry: dict[str, Any], experiment: str, *, verify: bool,
               size: int, iterations: int, warmup: int, repeats: int,
               device: int = 0, peer: int | None = None, variant: str | None = None,
               pattern: str | None = None, target: str | None = None, output_dir: Path | None = None,
               profile: bool = False, mode: str = "full") -> list[str]:
    if entry.get("runner") == "host":
        argv = [sys.executable, str(ROOT / "scripts" / "atlas_host.py"), "--experiment", experiment,
                "--build-dir", str(BUILD), "--output-dir", str(output_dir or ROOT / "benchmark_runs" / "active"),
                "--mode", "smoke" if verify or (profile and experiment == "E33") else mode,
                "--warmup", str(warmup), "--repeats", str(repeats)]
        if profile and experiment == "E33":
            argv.append("--profile-diagnostic")
    else:
        binary = BUILD / "bin" / str(target or entry["target"])
        argv = [str(binary), "--experiment", experiment, "--size", str(size),
                "--iterations", str(iterations), "--warmup", str(warmup),
                "--repeats", str(repeats), "--device", str(device)]
        if peer is not None:
            argv += ["--peer", str(peer)]
        if variant:
            argv += ["--variant", variant]
        if pattern:
            argv += ["--pattern", pattern]
    if verify:
        argv.append("--verify-only")
    if profile and entry.get("runner") != "host":
        argv.append("--profile-friendly")
    return argv


def archive_controller_files(outcome: dict[str, Any], run_dir: Path, label: str) -> list[str]:
    """Copy bounded controller receipts and command output into this run's evidence tree."""
    import shutil as _shutil
    saved: list[str] = []
    target = run_dir / "controller" / label
    target.mkdir(parents=True, exist_ok=True)
    anchor = outcome.get("stdout_path")
    if isinstance(anchor, str) and Path(anchor).is_file():
        artifact_dir = Path(anchor).parent
        try:
            _shutil.copytree(artifact_dir, target / "artifacts", dirs_exist_ok=True)
            saved.append(str((target / "artifacts").relative_to(run_dir)))
        except OSError:
            pass
    for key in ("stdout_path", "stderr_path", "lease_receipt"):
        source = outcome.get(key)
        if isinstance(source, str) and Path(source).is_file():
            dest = target / (key + Path(source).suffix)
            _shutil.copy2(source, dest)
            saved.append(str(dest.relative_to(run_dir)))
    return saved


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def report_text(results: dict[str, Any], run_dir: Path, ids: list[str], key: str) -> str:
    # These arguments remain explicit for call-site compatibility; the renderer
    # reads the persisted, schema-validated records to build the analysis too.
    del results, ids, key
    return atlas_report.render(run_dir)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "full"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--experiments", help="comma-separated E00..E39; default all")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--profiles", choices=("none", "focused"), default="focused")
    args = parser.parse_args()
    matrix = load_matrix()
    selected = [x.strip().upper() for x in args.experiments.split(",")] if args.experiments else [f"E{i:02d}" for i in range(40)]
    validate_ids(selected, matrix)
    ids = [f"E{i:02d}" for i in range(40)]
    if len(selected) != len(set(selected)):
        raise SystemExit("duplicate experiment IDs are not allowed")
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    run_uuid = str(uuid.uuid4())
    machine = machine_identity()
    tools = tool_versions()
    source = source_identity()
    config = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    # Compilation is CPU-side preparation. All benchmark, sanitizer, telemetry,
    # and profiler processes below still enter through the CUDA controller.
    build_configure = command_output(["cmake", "-S", str(ROOT), "-B", str(BUILD),
                                      f"-DCMAKE_CUDA_COMPILER={NVCC}", "-DCMAKE_CUDA_ARCHITECTURES=70"], timeout=90)
    build_result = (command_output(["cmake", "--build", str(BUILD), "--parallel", "4"], timeout=1800)
                    if build_configure["returncode"] == 0 else
                    {"returncode": None, "stdout": "", "stderr": "Skipped because CMake configuration failed."})
    build_record = {"configure": build_configure, "build": build_result,
                    "binary_sha256": binary_identity(matrix)}
    campaign_identity = {"mode": args.mode, "experiments": selected, "profiles": args.profiles,
                         "matrix_sha256": digest_file(MATRIX_PATH), "source": source,
                         "binaries": build_record["binary_sha256"],
                         "machine_sha256": digest_bytes(json.dumps(machine, sort_keys=True).encode()),
                         "tools_sha256": digest_bytes(json.dumps(tools, sort_keys=True).encode())}
    campaign_key = digest_bytes(json.dumps(campaign_identity, sort_keys=True).encode())
    # Resume only the newest matching finished/partial run and copy its validated records.
    results: dict[str, Any] = {}
    resume_config: dict[str, Any] | None = None
    resume_dir: Path | None = None
    if args.resume and output.is_dir():
        for candidate in sorted(output.glob("v100-*/run_config.json"), reverse=True):
            try:
                old_config = json.loads(candidate.read_text(encoding="utf-8"))
                old_results = json.loads((candidate.parent / "results.json").read_text(encoding="utf-8"))
                if resume_compatible(old_config, campaign_key):
                    results = {k: v for k, v in old_results.items() if k in selected}
                    if results:
                        resume_config = old_config
                        resume_dir = candidate.parent
                        break
            except (OSError, json.JSONDecodeError):
                continue
    if resume_dir is not None and resume_config is not None:
        run_dir = resume_dir
        run_uuid = str(resume_config.get("run_id", run_uuid))
        resume_config["resumed_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        write_json(run_dir / "run_config.json", resume_config)
    else:
        run_dir = output / ("v100-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + run_uuid[:8])
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "controller").mkdir()
        config_record = {"schema_version": 1, "run_id": run_uuid, "campaign_key": campaign_key,
                         "identity": campaign_identity, "machine": machine, "tools": tools,
                         "controller_runtime": controller_runtime_identity(),
                         "source": source, "matrix": config, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                         "mode": args.mode, "profiles": args.profiles, "experiments": selected,
                         "accounted_experiments": ids}
        write_json(run_dir / "run_config.json", config_record)
    write_json(run_dir / "build.json", build_record)
    write_json(run_dir / "results.json", results)
    uuids = gpu_uuids(machine)
    uuid_by_index = gpu_uuid_by_index(machine)
    if not uuids:
        gpu_unavailable = "GPU inventory unavailable; controller admission cannot be attempted"
    else:
        gpu_unavailable = ""

    build_ok = build_configure["returncode"] == 0 and build_result["returncode"] == 0

    for experiment in selected:
        if experiment in results and result_complete_for_resume(
                results[experiment], matrix["experiments"].get(experiment, {}), args.profiles):
            continue
        if experiment in RESTRICTED:
            results[experiment] = disposition(experiment, "NOT_RUN", limitations=[
                "The protocol requires restricted register/binary/command-level control; public CUDA interfaces do not exercise that hypothesis."])
            write_json(run_dir / "results.json", results)
            continue
        if args.mode == "smoke" and experiment == "E31":
            results[experiment] = disposition(experiment, "NOT_RUN", limitations=[
                "Private MPS lifecycle is reserved for a full-mode, controller-admitted run."])
            write_json(run_dir / "results.json", results)
            continue
        entry = matrix["experiments"][experiment]
        if gpu_unavailable and entry.get("runner") != "host":
            results[experiment] = disposition(experiment, "INCONCLUSIVE", limitations=[gpu_unavailable])
            write_json(run_dir / "results.json", results)
            continue
        failed_deps = dependency_failures(experiment, results, matrix)
        if failed_deps:
            results[experiment] = disposition(experiment, "INCONCLUSIVE", limitations=[
                "Correctness dependency failed: " + ", ".join(failed_deps)])
            write_json(run_dir / "results.json", results)
            continue
        if not build_ok:
            # One controller invocation carries the optional build as a pre-lease stage.
            # A cheap host experiment can run without the native binaries.
            if entry.get("runner") == "host":
                host_script = ROOT / "scripts" / "atlas_host.py"
                if not host_script.is_file():
                    results[experiment] = disposition(experiment, "INCONCLUSIVE", limitations=["Host runner script is not yet available."])
                    write_json(run_dir / "results.json", results); continue
            elif not build_ok:
                results[experiment] = disposition(experiment, "INCONCLUSIVE", limitations=[
                    "CMake configuration/build failed: " + (build_result.get("stderr") or build_configure.get("stderr") or build_result.get("stdout") or "unknown error")[-1000:]])
                write_json(run_dir / "results.json", results); continue

        settings = matrix["sweeps"][args.mode]
        cases: list[dict[str, Any]] = []
        limitations: list[str] = []
        raw_artifacts: list[str] = []
        experiment_uuids: list[str] = []
        sanitizer_checked: set[str] = set()
        status = ("CPU_ONLY" if entry.get("runner") == "host" and not entry.get("resource_group")
                  else "GPU_RUN")
        case_specs = entry.get("cases", [{"size": settings["size"], "iterations": settings["iterations"]}])
        # Smoke reduces all declared axes to the first deterministic case.
        if args.mode == "smoke":
            if experiment == "E32":
                cdp_case = next((case for case in case_specs if case.get("sanitizer") == "cdp"), None)
                case_specs = case_specs[:1] + ([cdp_case] if cdp_case is not None else [])
            else:
                case_specs = case_specs[:1]
        profile_indices = ({0, 1} if args.mode == "smoke" and experiment == "E32"
                           else focused_profile_indices(experiment, entry, case_specs))
        for ci, case_spec in enumerate(case_specs):
            size = int(case_spec.get("size", settings["size"]))
            iterations = int(case_spec.get("iterations", settings["iterations"]))
            warmup = int(settings["warmups"])
            repeats = int(settings["repeats"])
            host = entry.get("runner") == "host"
            case_target = str(case_spec.get("target", entry.get("target", "")))
            if host:
                device_ids = uuids[:1] if entry.get("resource_group") == "single" else []
                recipe = "baseline"
                cmd = child_argv(entry, experiment, verify=False, size=size, iterations=iterations,
                                 warmup=warmup, repeats=repeats, output_dir=run_dir / "host",
                                 mode=args.mode)
            else:
                group = entry.get("resource_group", "single")
                device_ids = (uuids if group == "all" else
                              [uuid_by_index[i] for i in (0, 2) if i in uuid_by_index] if group == "pair" else
                              uuids[:1])
                required_devices = {"single": 1, "pair": 2, "all": 4}.get(group, 1)
                if len(device_ids) != required_devices:
                    status = "INCONCLUSIVE"; limitations.append(
                        f"Resource group {group!r} requires {required_devices} matching GPU UUIDs; found {len(device_ids)}."); break
                experiment_uuids.extend(device_ids)
                # Device ordinals inside CUDA_VISIBLE_DEVICES are lease-local.
                try:
                    device, peer = lease_ordinals(case_spec, group, len(device_ids))
                except (TypeError, ValueError) as exc:
                    status = "INCONCLUSIVE"; limitations.append(f"Invalid lease-local device/peer ordinal: {exc}"); break
                recipe = "baseline"
                cmd = child_argv(entry, experiment, verify=False, size=size, iterations=iterations,
                                 warmup=warmup, repeats=repeats, device=device, peer=peer,
                                 variant=case_spec.get("variant"), pattern=case_spec.get("pattern"),
                                 target=case_target)
            binary_rel = [] if host else [str((BUILD / "bin" / case_target).relative_to(ROOT))]
            if host:
                outcome = controller_call(cmd, recipe="baseline", uuids=device_ids,
                                          timeout=int(entry.get("timeout", 120)), binary_paths=[])
                saved = archive_controller_files(outcome, run_dir, experiment + "-host")
                raw_artifacts.extend(saved)
                experiment_uuids.extend(device_ids)
                if saved:
                    write_json(run_dir / "controller" / f"{experiment}-host-files.json", saved)
                capture = read_capture(outcome.get("stdout_path"))
                problem = capture_problem(outcome, capture)
                if problem is None:
                    try:
                        c, good = normalize_cases(capture, experiment); cases.extend(c)
                        if not good: status = "INCONCLUSIVE"; limitations.append("A host correctness check reported failure.")
                        if not outcome.get("ok"):
                            status = "INCONCLUSIVE"; limitations.append("Controller invalidated the host stage despite a retained result document.")
                        if any(x.get("status") == "INCONCLUSIVE" for x in c):
                            status = "INCONCLUSIVE"; limitations.append("Host runner reported an inconclusive case.")
                        if entry.get("resource_group") == "single" and not any(x.get("status") == "GPU_RUN" for x in c):
                            status = "INCONCLUSIVE"; limitations.append("Host stage held a GPU lease but returned no GPU_RUN evidence.")
                    except ValueError as exc:
                        status = "INCONCLUSIVE"; limitations.append(f"Host runner JSON contract failed: {exc}")
                else:
                    status = "INCONCLUSIVE"; limitations.append(
                        "Controller host stage did not yield machine-readable evidence: " +
                        json.dumps({"problem": problem, **outcome}, sort_keys=True)[:1500])
                if (args.profiles == "focused" and entry.get("nsys_eligible", False)
                        and (status != "INCONCLUSIVE" or experiment == "E33")):
                    profile_cmd = child_argv(entry, experiment, verify=False, size=0, iterations=0,
                                             warmup=warmup, repeats=repeats,
                                             output_dir=run_dir / "host-profile" / experiment,
                                             profile=True)
                    profile = controller_call(profile_cmd, recipe="nsys", uuids=device_ids,
                                              timeout=int(entry.get("profile_timeout", 300)), binary_paths=[])
                    raw_artifacts.extend(archive_controller_files(profile, run_dir, f"{experiment}-nsys-host"))
                    evidence_valid, evidence = validate_profile_artifacts("nsys", profile)
                    representative = (cases[0] if experiment == "E33" and cases else
                                      next((c for c in cases if c.get("status") == "GPU_RUN"), None))
                    if representative is not None:
                        representative.setdefault("profiles", {})["nsys"] = evidence
                    if experiment == "E33":
                        if not evidence_valid:
                            limitations.append("E33 diagnostic Nsight Systems capture was unavailable or invalid: " +
                                               json.dumps(evidence, sort_keys=True)[:1200])
                        elif not profile.get("ok"):
                            limitations.append("E33 diagnostic profiler child returned nonzero, but the retained GPU timeline is diagnostic only and does not change the steady-state disposition.")
                        limitations.append("Nsight Systems used a separate smoke-mode diagnostic burst; it does not establish steady-state energy or timing.")
                    elif not evidence_valid or not profile.get("ok"):
                        status = "INCONCLUSIVE"
                        limitations.append("Host-stage Nsight Systems capture failed validation: " +
                                           json.dumps(evidence, sort_keys=True)[:1200])
                if args.mode == "full":
                    short_cases = [(c.get("variant", "case"), full_timing_sample_problem(c))
                                   for c in cases if c.get("status") == "GPU_RUN"]
                    short_cases = [(name, problem) for name, problem in short_cases if problem]
                    if short_cases:
                        status = "INCONCLUSIVE"
                        limitations.append("Full mode requires at least 30 unprofiled raw timing samples per executed host GPU case: " +
                                           json.dumps(short_cases[:8], sort_keys=True))
                continue

            verify_cmd = child_argv(entry, experiment, verify=True, size=size, iterations=iterations,
                                    warmup=0, repeats=1, device=device,
                                    peer=peer,
                                    variant=case_spec.get("variant"), pattern=case_spec.get("pattern"),
                                    target=case_target,
                                    output_dir=run_dir / "host")
            verify = controller_call(verify_cmd, recipe="baseline", uuids=device_ids,
                                     timeout=int(entry.get("timeout", 120)), binary_paths=binary_rel)
            raw_artifacts.extend(archive_controller_files(verify, run_dir, f"{experiment}-verify-{ci}"))
            child_valid, child_evidence = validate_child_correctness(verify, experiment)
            if not child_valid:
                status = "INCONCLUSIVE"
                limitations.append("Controller correctness/oracle gate failed: " + json.dumps(child_evidence, sort_keys=True)[:1500])
                continue
            if child_evidence.get("unsupported_only"):
                unsupported = child_evidence.get("normalized_cases", [])
                cases.extend(unsupported)
                reasons = [f"{c.get('variant', 'case')}: {'; '.join(c.get('limitations', [])) or 'unsupported capability'}"
                           for c in unsupported]
                limitations.extend(reasons)
                continue
            # Every case receives an independent correctness check. Run expensive
            # sanitizer variants once on the first deterministic representative
            # for each family/experiment; this still covers every kernel module.
            sanitizer_kind = str(case_spec.get("sanitizer", entry.get("sanitizer", "ordinary")))
            sanitizer_key = case_target + ":" + sanitizer_kind
            if sanitizer_key not in sanitizer_checked:
                sanitizer_checked.add(sanitizer_key)
                memory_check = controller_call(verify_cmd, recipe="compute-sanitizer", uuids=device_ids,
                                               timeout=int(entry.get("sanitizer_timeout", 180)), binary_paths=binary_rel)
                raw_artifacts.extend(archive_controller_files(memory_check, run_dir, f"{experiment}-memcheck-{ci}"))
                memory_valid, memory_evidence = validate_sanitizer_outcome(memory_check, "memcheck", child_valid=child_valid)
                if not memory_valid:
                    status = "INCONCLUSIVE"; limitations.append("Compute Sanitizer memcheck failed validation: " + json.dumps(memory_evidence, sort_keys=True)[:1500]); continue
                # Shared memory / synchronization families receive race and synccheck.
                if sanitizer_kind in {"shared", "sync", "tensor", "communication"}:
                    for tool in ("racecheck", "synccheck"):
                        check_cmd = [str(SANITIZER), "--tool", tool, "--error-exitcode", "99", *verify_cmd]
                        check = controller_call(check_cmd, recipe="baseline", uuids=device_ids,
                                                timeout=int(entry.get("sanitizer_timeout", 180)), binary_paths=binary_rel)
                        raw_artifacts.extend(archive_controller_files(check, run_dir, f"{experiment}-{tool}-{ci}"))
                        check_valid, check_evidence = validate_sanitizer_outcome(check, tool, child_valid=child_valid)
                        if not check_valid:
                            status = "INCONCLUSIVE"; limitations.append(f"Compute Sanitizer {tool} failed validation: " + json.dumps(check_evidence, sort_keys=True)[:1200])
            if status == "INCONCLUSIVE":
                continue
            outcome = controller_call(cmd, recipe=recipe, uuids=device_ids,
                                      timeout=int(entry.get("timeout", 120)), binary_paths=binary_rel)
            raw_artifacts.extend(archive_controller_files(outcome, run_dir, f"{experiment}-timing-{ci}"))
            capture = read_capture(outcome.get("stdout_path"))
            problem = capture_problem(outcome, capture)
            if problem is None:
                try:
                    c, good = normalize_cases(capture, experiment); cases.extend(c)
                    if sanitizer_kind == "cdp":
                        for case in c:
                            case.setdefault("limitations", []).append(
                                "Racecheck and synccheck are not applicable to this device-side child-launch executable; memcheck was run.")
                    if not good:
                        status = "INCONCLUSIVE"; limitations.append("A measured case failed its correctness check.")
                    if not outcome.get("ok"):
                        status = "INCONCLUSIVE"; limitations.append("Controller invalidated the measurement despite a retained result document.")
                    if any(x.get("status") == "INCONCLUSIVE" for x in c):
                        status = "INCONCLUSIVE"; limitations.append("Benchmark reported an inconclusive case.")
                except ValueError as exc:
                    status = "INCONCLUSIVE"; limitations.append(f"Benchmark JSON contract failed: {exc}")
            else:
                status = "INCONCLUSIVE"; limitations.append("Controller timing run failed: " + problem + "; " + json.dumps(outcome, sort_keys=True)[:1500])
            # Focused profiling is serialized after timing. A capture failure remains visible.
            if args.profiles == "focused" and entry.get("nsys_eligible", False) and ci in profile_indices and status != "INCONCLUSIVE":
                for profile_recipe in ("nsys", "ncu"):
                    if profile_recipe == "ncu" and not entry.get("ncu_replay_safe", False):
                        continue
                    if profile_recipe == "nsys":
                        profile_cmd = cmd
                    else:
                        profile_cmd = child_argv(entry, experiment, verify=False, size=size,
                                                 iterations=iterations, warmup=1, repeats=12,
                                                 device=device, peer=peer,
                                                 variant=case_spec.get("variant"),
                                                 pattern=case_spec.get("pattern"), profile=True)
                    profile = controller_call(profile_cmd, recipe=profile_recipe, uuids=device_ids,
                                              timeout=int(entry.get("profile_timeout", 300)), binary_paths=binary_rel)
                    raw_artifacts.extend(archive_controller_files(profile, run_dir, f"{experiment}-{profile_recipe}-{ci}"))
                    evidence_valid, evidence = validate_profile_artifacts(profile_recipe, profile)
                    if cases:
                        cases[-1].setdefault("profiles", {})[profile_recipe] = evidence
                    if not evidence_valid:
                        status = "INCONCLUSIVE"
                        limitations.append(f"{profile_recipe} wrapper returned {profile.get('returncode')}; report validation failed: {json.dumps(evidence, sort_keys=True)[:1200]}")
                    elif not profile.get("ok"):
                        status, profile_problem = profile_failure(status, profile, profile_recipe)
                        if profile_problem:
                            limitations.append(profile_problem)
                if not entry.get("ncu_replay_safe", False):
                    limitations.append("Nsight Compute replay was not run for this synchronization, communication, or progress-sensitive workload.")
        status, completion_reason = finalize_native_status(status, cases)
        if completion_reason:
            limitations.append(completion_reason)
        if args.mode == "full":
            short_cases = [(c.get("variant", "case"), full_timing_sample_problem(c))
                           for c in cases if c.get("status") == "GPU_RUN"]
            short_cases = [(name, problem) for name, problem in short_cases if problem]
            if short_cases:
                status = "INCONCLUSIVE"
                limitations.append("Full mode requires at least 30 unprofiled raw timing samples per executed GPU case: " +
                                   json.dumps(short_cases[:8], sort_keys=True))
        results[experiment] = disposition(experiment, status, cases=cases, limitations=limitations,
                                          hardware={"gpu_uuids": sorted(set(experiment_uuids))}, software={"tools": tools},
                                          protocol={"matrix": entry, "mode": args.mode},
                                          raw_artifacts=sorted(set(raw_artifacts)))
        results[experiment]["source_hashes"] = source
        write_json(run_dir / "results.json", results)
        (run_dir / "REPORT.md").write_text(report_text(results, run_dir, ids, campaign_key), encoding="utf-8")

    # Every run states a disposition for all forty protocols, even when a subset was selected.
    for experiment in ids:
        if experiment not in results:
            results[experiment] = disposition(experiment, "NOT_RUN", limitations=[
                "Not selected for this campaign run."])
    write_json(run_dir / "results.json", results)
    selected_incomplete_reasons = [e + ": disposition is INCONCLUSIVE" for e in selected
                                   if results[e]["status"] == "INCONCLUSIVE"]
    selected_incomplete_reasons.extend(
        e + ": required profiler evidence is missing" for e in selected if e not in RESTRICTED
        and not has_required_profiles(results[e], matrix["experiments"].get(e, {}), args.profiles))
    if args.mode != "full":
        selected_incomplete_reasons.append("diagnostic smoke mode is not final campaign evidence")
    selected_incomplete = bool(selected_incomplete_reasons)
    validate_result_records(results)
    correctness_summary = {
        "passed": [e for e in selected if results[e]["correctness"].get("valid") is True],
        "failed": [e for e in selected if results[e]["correctness"].get("valid") is False],
        "unknown_or_not_run": [e for e in selected if results[e]["correctness"].get("valid") is None],
    }
    profile_summary = {
        "required": [e for e in selected if e not in RESTRICTED and matrix["experiments"].get(e, {}).get("nsys_eligible")],
        "missing": [e for e in selected if e not in RESTRICTED and matrix["experiments"].get(e, {}).get("nsys_eligible")
                    and not has_required_profiles(results[e], matrix["experiments"][e], args.profiles)],
    }
    (run_dir / "summary.json").write_text(json.dumps({"campaign_key": campaign_key,
        "counts": {s: sum(r["status"] == s for r in results.values()) for s in sorted(ALLOWED_STATUSES)},
        "selected": selected, "accounted": ids,
        "selected_complete": args.mode == "full" and not selected_incomplete,
        "complete": args.mode == "full" and set(selected) == set(ids) and not selected_incomplete,
        "completion_blockers": selected_incomplete_reasons,
        "correctness": correctness_summary, "profiling": profile_summary},
        indent=2, sort_keys=True) + "\n", encoding="utf-8")
    atlas_report.write_report(run_dir)
    return 0 if args.mode == "smoke" else (2 if selected_incomplete else 0)


if __name__ == "__main__":
    raise SystemExit(main())
