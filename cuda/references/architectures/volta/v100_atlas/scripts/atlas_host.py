#!/usr/bin/env python3
"""Read-only host stages and tightly scoped MPS/steady-state campaign stages.

All stdout is one JSON object using the native benchmark case contract. Host
diagnostics and retained command failures are written to the artifact directory.
The MPS and E33 paths require a nonempty TODO_GPU_LEASE_RECEIPT; admission itself
is owned by the external Project Control GPU runner.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import statistics
import subprocess
import sys
import threading
import tempfile
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT = 90


def _case(experiment: str, variant: str, status: str, *, valid: bool,
          configuration: dict[str, Any] | None = None,
          metrics: dict[str, float] | None = None,
          samples: dict[str, list[float]] | None = None,
          limitations: list[str] | None = None) -> dict[str, Any]:
    return {"experiment": experiment, "variant": variant, "status": status,
            "configuration": configuration or {}, "metrics": metrics or {},
            "samples": samples or {}, "checks": {"valid": bool(valid)},
            "limitations": limitations or []}


def _result(experiment: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {"experiment": experiment,
            "checks": {"valid": bool(cases) and all(c["checks"]["valid"] for c in cases)},
            "cases": cases}


def _emit(result: dict[str, Any]) -> None:
    print(json.dumps(result, sort_keys=True, allow_nan=False))


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _run(argv: list[str], *, timeout: float = DEFAULT_TIMEOUT,
         env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        p = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout, env=env, check=False)
        return {"argv": argv, "returncode": p.returncode, "stdout": p.stdout,
                "stderr": p.stderr, "timed_out": False}
    except subprocess.TimeoutExpired as e:
        return {"argv": argv, "returncode": None,
                "stdout": (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
                "stderr": (e.stderr or b"").decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or ""),
                "timed_out": True}
    except OSError as e:
        return {"argv": argv, "returncode": None, "stdout": "", "stderr": str(e), "timed_out": False}


def _tool(name: str, fallback: str | None = None) -> str | None:
    configured = os.environ.get("ATLAS_" + name.upper().replace("-", "_") + "")
    return configured or shutil.which(name) or fallback


def _hardware() -> dict[str, Any]:
    return {"hostname": platform.node(), "system": platform.platform(),
            "machine": platform.machine(), "python": sys.version.split()[0]}


def _save_raw(out: Path, label: str, data: dict[str, Any]) -> None:
    _write(out / "host" / (label + ".json"), data)


def _inventory(build: Path, out: Path) -> tuple[dict[str, Any], list[str]]:
    calls: dict[str, Any] = {}
    errors: list[str] = []
    cap = build / "bin" / "atlas_capability"
    if not cap.is_file():
        cap = build / "atlas_capability"
    if cap.is_file():
        calls["driver_api"] = _run([str(cap)])
    else:
        calls["driver_api"] = {"returncode": None, "stdout": "", "stderr": f"missing executable: {cap}", "timed_out": False}
    for label, args in (("smi_query", ["nvidia-smi", "--query-gpu=index,uuid,name,pci.bus_id,compute_cap,driver_version,memory.total,power.limit,power.draw,clocks.current.sm,clocks.current.memory,temperature.gpu,ecc.mode.current", "--format=csv,noheader,nounits"]),
                        ("smi_xml", ["nvidia-smi", "-q", "-x"]),
                        ("topology", ["nvidia-smi", "topo", "-m"])):
        calls[label] = _run(args)
    for label, argv in calls.items():
        if argv.get("returncode") != 0:
            errors.append(f"{label}: {argv.get('stderr') or 'command failed'}")
    numa: dict[str, Any] = {"nodes": None, "device_links": []}
    node_root = Path("/sys/devices/system/node")
    nodes = sorted(p.name for p in node_root.glob("node[0-9]*") if p.is_dir())
    numa["nodes"] = nodes or None
    for dev in sorted(Path("/sys/bus/pci/devices").glob("*")):
        try:
            vendor = (dev / "vendor").read_text().strip()
            if vendor.lower() != "0x10de":
                continue
            rec: dict[str, Any] = {"bdf": dev.name}
            for attr in ("numa_node", "local_cpulist", "current_link_width", "current_link_speed", "max_link_width", "max_link_speed"):
                f = dev / attr
                try:
                    rec[attr] = f.read_text().strip()
                except OSError as e:
                    rec[attr] = None
                    rec[attr + "_error"] = str(e)
            numa["device_links"].append(rec)
        except OSError as e:
            errors.append(f"PCI sysfs {dev.name}: {e}")
    calls["numa_pcie_sysfs"] = numa
    _save_raw(out, "inventory", calls)
    return calls, errors


def run_e00(a: argparse.Namespace) -> dict[str, Any]:
    raw, errors = _inventory(a.build_dir, a.output_dir)
    metrics = {"device_count": float(len(re.findall(r'"ordinal"\s*:', raw.get("driver_api", {}).get("stdout", ""))))}
    return _result("E00", [_case("E00", "readonly_inventory", "CPU_ONLY" if not errors else "INCONCLUSIVE",
        valid=not errors, configuration={"read_only": True}, metrics=metrics,
        limitations=errors + ["Inventory records reported capabilities; no allocation, peer enabling, launch, or clock changes were performed."])])


def run_e01(a: argparse.Namespace) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("atlas_semantic_checks", ROOT / "tools" / "semantic_checks.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import tools/semantic_checks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run()
    _write(a.output_dir / "host" / "E01_semantic_checks.json", result)
    groups = result.get("groups", [])
    passed = result.get("status") == "PASS"
    metrics = {"assertions": float(result.get("assertions", 0)), "test_groups": float(len(groups))}
    return _result("E01", [_case("E01", "cpu_semantics", "CPU_ONLY" if passed else "INCONCLUSIVE",
        valid=passed, configuration={"seed": result.get("seed"), "gpu_measured": False}, metrics=metrics,
        limitations=list(result.get("limitations", [])) + ["Original CPU_TEST_RESULTS ledger was not modified."])])


def run_e34(a: argparse.Namespace) -> dict[str, Any]:
    inv, errors = _inventory(a.build_dir, a.output_dir)
    _save_raw(a.output_dir, "E34_readonly_ras", inv)
    return _result("E34", [_case("E34", "read_only_ras_status", "CPU_ONLY" if not errors else "INCONCLUSIVE",
        valid=not errors, configuration={"read_only": True, "fault_injection": False},
        limitations=errors + ["Read-only nvidia-smi ECC/platform status was collected; absence of a reported error is not proof of error-free hardware."])])


def run_e35(a: argparse.Namespace) -> dict[str, Any]:
    inv, errors = _inventory(a.build_dir, a.output_dir)
    _save_raw(a.output_dir, "E35_platform_evidence", inv)
    return _result("E35", [_case("E35", "software_visible_platform", "CPU_ONLY" if not errors else "INCONCLUSIVE",
        valid=not errors, configuration={"physical_modification": False},
        limitations=errors + ["Software-visible SKU, BDF, topology, link and NUMA evidence only; board wiring and rails remain unknown."])])


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run_e36(a: argparse.Namespace) -> dict[str, Any]:
    nvcc = _tool("nvcc", "/usr/local/cuda-12.9/bin/nvcc")
    cuobjdump = _tool("cuobjdump", "/usr/local/cuda-12.9/bin/cuobjdump")
    compiler = _run([nvcc, "--version"]) if nvcc else {"stderr": "nvcc unavailable", "returncode": None}
    reports: dict[str, Any] = {"nvcc": compiler, "binaries": [], "source_hashes": {}}
    failures = []
    if compiler.get("returncode") != 0:
        failures.append("nvcc version could not be queried")
    for path in [ROOT / "CMakeLists.txt", *sorted((ROOT / "benchmarks" / "native").glob("*.cu")),
                 *sorted((ROOT / "benchmarks" / "native").glob("*.hpp")), ROOT / "benchmarks" / "capability_probe.cpp"]:
        if path.is_file():
            reports["source_hashes"][str(path.relative_to(ROOT))] = _sha(path)
    bins = sorted(p for p in (a.build_dir / "bin").glob("*") if p.is_file()) if (a.build_dir / "bin").exists() else []
    for path in bins:
        entry: dict[str, Any] = {"path": str(path), "sha256": _sha(path), "size_bytes": path.stat().st_size}
        if cuobjdump:
            # List embedded ELF images only; do not dump SASS broadly.
            entry["elf_images"] = _run([cuobjdump, "--list-elf", str(path)], timeout=30)
            no_device_code = "does not contain device code" in entry["elf_images"].get("stderr", "").lower()
            if no_device_code and path.name == "atlas_capability":
                entry["device_code_present"] = False
                entry["classification"] = "host_only_driver_api_inventory"
            elif entry["elf_images"].get("returncode") != 0:
                failures.append(f"cuobjdump could not list images in {path.name}")
            elif "sm_70" not in entry["elf_images"].get("stdout", ""):
                failures.append(f"{path.name} has no listed native sm_70 ELF image")
            else:
                entry["device_code_present"] = True
        else:
            entry["elf_images"] = {"returncode": None, "stderr": "cuobjdump unavailable"}
            failures.append("cuobjdump unavailable")
        reports["binaries"].append(entry)
    if not bins:
        failures.append("no compiled binaries found under build/bin")
    _save_raw(a.output_dir, "E36_toolchain", reports)
    return _result("E36", [_case("E36", "toolchain_native_image_qualification", "COMPILED_ONLY" if not failures else "INCONCLUSIVE",
        valid=not failures, configuration={"target_architecture": "sm_70", "nvcc": nvcc, "cuobjdump": cuobjdump},
        metrics={"binary_count": float(len(bins))}, limitations=failures + ["Image listing is metadata inspection; no conclusion about runtime operator coverage is implied."])])


def run_e38(a: argparse.Namespace) -> dict[str, Any]:
    falsifiers = [
        {"claim": "partial-warp tensor-core participation is a supported public contract", "falsifier": "No documented public interface accepts an incomplete participating warp for the selected operation; exact reference semantics and participation contract are absent."},
        {"claim": "GPU DMA engines perform arbitrary array reductions", "falsifier": "Public copy/async interfaces move data but do not specify reduction semantics; equivalent supported work must execute explicit arithmetic."},
        {"claim": "peer memory is automatically coherent for every access pattern", "falsifier": "Peer reachability flags do not establish ordering, atomic scope, or cache coherence; each operation needs a documented memory-model contract."},
        {"claim": "generic semiring MMA is available on sm70", "falsifier": "Public WMMA/MMA interfaces define supported arithmetic forms; an arbitrary semiring requires an independently specified supported mapping."},
        {"claim": "header or mnemonic presence proves undocumented opcode support", "falsifier": "Compilation and documentation evidence must establish target encoding and runtime contract; malformed opcodes are excluded."},
    ]
    _write(a.output_dir / "host" / "E38_falsifiers.json", falsifiers)
    cases = [_case("E38", re.sub(r"[^a-z0-9]+", "_", item["claim"].lower()).strip("_")[:56], "CPU_ONLY",
                   valid=True, configuration={"method": "offline_contract_falsification"},
                   limitations=[item["falsifier"], "Falsifies the stated general interpretation only; does not prove physical impossibility."])
             for item in falsifiers]
    return _result("E38", cases)


def _lease_ok(device: int) -> tuple[bool, str, dict[str, Any]]:
    """Validate the live foreground-controller receipt and visible GPU identity."""
    raw = os.environ.get("TODO_GPU_LEASE_RECEIPT", "").strip()
    if not raw:
        return False, "TODO_GPU_LEASE_RECEIPT is missing; controller GPU admission was not established.", {}
    try:
        path = Path(raw).resolve(strict=True)
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("receipt must be an object")
        ids = receipt.get("resource_ids")
        if (receipt.get("format") != "CUDA-FOREGROUND-LEASE/1" or receipt.get("state") != "active"
                or receipt.get("project_root") != str(ROOT)
                or not isinstance(ids, list) or not ids
                or not all(isinstance(x, str) and re.fullmatch(r"accelerator:GPU-[A-Fa-f0-9-]+", x) for x in ids)
                or len(set(ids)) != len(ids)):
            raise ValueError("foreground lease format, state, project, or resources did not validate")
        owner = receipt.get("owner_id")
        owner_uuid = owner.removeprefix("foreground:") if isinstance(owner, str) else ""
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", owner_uuid):
            raise ValueError("foreground owner identity is missing or malformed")
        pid = receipt.get("pid")
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 1:
            raise ValueError("foreground controller PID is missing or invalid")
        os.kill(pid, 0)
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ")
        if b"cuda_controller.py" not in cmdline:
            raise ValueError("lease owner is not the CUDA foreground controller")
        ancestor = os.getpid()
        descended = False
        visited: set[int] = set()
        for _ in range(32):
            if ancestor == pid:
                descended = True
                break
            if ancestor <= 1 or ancestor in visited:
                break
            visited.add(ancestor)
            status = Path(f"/proc/{ancestor}/status").read_text(encoding="utf-8")
            parent_match = re.search(r"^PPid:\s*(\d+)\s*$", status, re.MULTILINE)
            if not parent_match:
                break
            ancestor = int(parent_match.group(1))
        if not descended:
            raise ValueError("current benchmark process is not descended from the receipt's CUDA controller")
        visible = [x.strip() for x in os.environ.get("CUDA_VISIBLE_DEVICES", "").split(",") if x.strip()]
        expected = sorted(x.removeprefix("accelerator:") for x in ids)
        if len(visible) != len(ids) or not visible:
            raise ValueError("controller visible-device count does not match the active lease")
        if not 0 <= device < len(visible):
            raise ValueError("requested logical device is outside the leased visible-device set")
        query = _run(["nvidia-smi", "--query-gpu=uuid,index", "--format=csv,noheader,nounits"], timeout=10)
        if query.get("returncode") != 0:
            raise ValueError("could not map visible devices to physical GPU UUIDs")
        by_index: dict[str, str] = {}
        for row in csv.reader(query.get("stdout", "").splitlines()):
            if len(row) != 2:
                raise ValueError("malformed GPU identity query")
            by_index[row[1].strip()] = row[0].strip()
        visible_uuids = [token if token.startswith("GPU-") else by_index.get(token) for token in visible]
        if any(not x for x in visible_uuids) or sorted(visible_uuids) != expected:
            raise ValueError("visible GPU UUIDs do not match the active foreground lease")
        return True, "", {"receipt_path": str(path), "owner_pid": pid,
                           "resource_uuids": expected, "selected_uuid": visible_uuids[device]}
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as e:
        return False, f"foreground GPU lease validation failed: {type(e).__name__}: {e}", {}


def _logic_argv(exe: Path, *, variant: str, device: int, warmup: int, repeats: int,
                size: int, iterations: int) -> list[str]:
    # Native benchmark binaries consume --experiment and --variant flags.
    return [str(exe), "--experiment", "E03", "--variant", variant, "--device", str(device),
            "--size", str(size), "--iterations", str(iterations), "--warmup", str(warmup), "--repeats", str(repeats)]


def _parse_native(text: str, expected_variant: str, expected_samples: int = 30) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except Exception as e:
        raise ValueError(f"native benchmark stdout is not JSON: {e}") from e
    if data.get("experiment") != "E03" or not isinstance(data.get("cases"), list) or not data["cases"]:
        raise ValueError("native JSON is missing the expected experiment/cases contract")
    if data.get("checks", {}).get("valid") is not True:
        raise ValueError("native benchmark reported failed correctness checks")
    matches = [case for case in data["cases"] if case.get("variant") == expected_variant]
    if len(matches) != 1:
        raise ValueError(f"native JSON must contain exactly one {expected_variant!r} variant")
    case = matches[0]
    if case.get("status") != "GPU_RUN":
        raise ValueError("native case status is not GPU_RUN")
    if case.get("checks", {}).get("valid") is not True:
        raise ValueError("native benchmark contains an invalid case")
    sample_arrays = case.get("samples", {})
    candidates = [(name, values) for name, values in sample_arrays.items()
                  if any(tag in name.lower() for tag in ("elapsed", "kernel", "wall", "time", "event"))]
    valid_candidates = []
    for name, values in candidates:
        if not isinstance(values, list) or not all(not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x) for x in values):
            raise ValueError("native timing samples are malformed or non-finite")
        if len(values) >= expected_samples:
            valid_candidates.append((name, [float(x) for x in values]))
    if not valid_candidates:
        raise ValueError(f"native {expected_variant} case has fewer than {expected_samples} timing samples")
    data["_validated_variant"] = expected_variant
    data["_validated_samples"] = valid_candidates[0][1]
    data["_validated_case"] = case
    return data


def _summarize_native(data: dict[str, Any]) -> tuple[list[float], list[str]]:
    return list(data["_validated_samples"]), [str(data["_validated_variant"])]


def _actual_work_contract(data: dict[str, Any]) -> dict[str, int]:
    """Read E03 work from the child-reported launch configuration, never argv."""
    case = data["_validated_case"]
    config = case.get("configuration", {})
    metrics = case.get("metrics", {})

    def int_value(*names: str) -> int | None:
        for name in names:
            value = config.get(name)
            if value is None:
                value = metrics.get(name)
            try:
                n = int(value)
            except (TypeError, ValueError):
                continue
            if n >= 0:
                return n
        return None

    logical = int_value("logical_threads", "elements", "size")
    launched = int_value("launched_threads", "actual_launched_threads", "threads") or logical
    iterations = int_value("iterations", "actual_iterations_per_working_thread")
    integer = int_value("integer_work")
    floating = int_value("fp_work")
    total = int_value("launched_total_work_units")
    if total is None and launched is not None and integer is not None and floating is not None:
        total = launched * (integer + floating)
    if logical is None or launched is None or iterations is None or integer is None or floating is None or total is None:
        raise ValueError("E03 output lacks the actual element/thread/work configuration required for normalization")
    if total != launched * (integer + floating):
        raise ValueError("E03 launched_total_work_units disagrees with launched threads and integer/fp work")
    reported_metric = metrics.get("launched_total_work_units")
    if reported_metric is not None and int(reported_metric) != total:
        raise ValueError("E03 reported work metric disagrees with its launch configuration")
    return {"logical_threads": logical, "launched_threads": launched, "iterations": iterations,
            "integer_work_per_thread": integer, "fp_work_per_thread": floating,
            "work_units_per_sample": total}


def _spawn(argv: list[str], env: dict[str, str], timeout: float) -> dict[str, Any]:
    """Run in a private process group so timeouts/signals reap only our clients."""
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         env=env, start_new_session=True)
    try:
        stdout, stderr = p.communicate(timeout=timeout)
        return {"argv": argv, "returncode": p.returncode, "stdout": stdout, "stderr": stderr, "timed_out": False}
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        try:
            os.killpg(p.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            p.communicate()
        if isinstance(sys.exc_info()[1], KeyboardInterrupt):
            raise
        return {"argv": argv, "returncode": p.returncode, "stdout": "", "stderr": "client timed out", "timed_out": True}


def _reap_clients(processes: list[subprocess.Popen[str]]) -> None:
    """Terminate and reap only child process groups created by this invocation."""
    for proc in processes:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    for proc in processes:
        if proc.poll() is None:
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.communicate()


def _mps_control(control: str, env: dict[str, str], command: str, timeout: float = 10) -> str:
    p = subprocess.run([control], input=command + "\n", text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout, env=env, check=False)
    if p.returncode != 0:
        raise RuntimeError(f"MPS control command failed: {p.stderr.strip()}")
    return p.stdout.strip()


def _mps_process_matches(pid: int, pipe: Path) -> bool:
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
        environ = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    except OSError:
        return False
    return (b"nvidia-cuda-mps" in cmdline and
            (b"CUDA_MPS_PIPE_DIRECTORY=" + os.fsencode(pipe)) in environ)


def _process_uses_private_pipe(pid: int, pipe: Path) -> bool:
    try:
        environ = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
    except OSError:
        return False
    return (b"CUDA_MPS_PIPE_DIRECTORY=" + os.fsencode(pipe)) in environ


def _private_mps_pids(pipe: Path) -> list[int]:
    owned = []
    proc = Path("/proc")
    for entry in proc.iterdir():
        if entry.name.isdigit() and _process_uses_private_pipe(int(entry.name), pipe):
            owned.append(int(entry.name))
    return sorted(owned)


def _mps_server_pids(server_list: str) -> list[int]:
    """Parse the PID list returned by the MPS control server."""
    return sorted({int(value) for value in re.findall(r"\b\d{2,}\b", server_list)})


def run_e31(a: argparse.Namespace) -> dict[str, Any]:
    ok, why, lease = _lease_ok(a.device)
    exe = a.build_dir / "bin" / "atlas_logic"
    if not ok:
        return _result("E31", [_case("E31", "private_mps_interference", "INCONCLUSIVE", valid=False, limitations=[why])])
    if not exe.is_file():
        return _result("E31", [_case("E31", "private_mps_interference", "INCONCLUSIVE", valid=False, limitations=[f"missing executable: {exe}"])])
    out = a.output_dir / "host" / "E31"
    out.mkdir(parents=True, exist_ok=True)
    client_env = os.environ.copy()
    client_env.pop("CUDA_MPS_PIPE_DIRECTORY", None)
    client_env.pop("CUDA_MPS_LOG_DIRECTORY", None)
    cases = []
    baseargv = _logic_argv(exe, variant="serial", device=a.device, warmup=5, repeats=30, size=65536, iterations=256)
    baseline = _run(baseargv, timeout=a.case_timeout, env=client_env)
    _write(out / "baseline.json", baseline)
    try:
        native = _parse_native(baseline["stdout"], "serial")
        vals, _ = _summarize_native(native)
        if baseline["returncode"] != 0 or not vals:
            raise ValueError("baseline returned no valid timing samples")
        cases.append(_case("E31", "single_client_baseline", "GPU_RUN", valid=True,
            configuration={"device": a.device, "gpu_uuid": lease["selected_uuid"], "clients": 1, "size": 65536, "iterations": 256},
            metrics={"median_ms": statistics.median(vals), "p95_ms": sorted(vals)[min(len(vals)-1, math.ceil(.95*len(vals))-1)]},
            samples={"elapsed_ms": vals}, limitations=["CUDA profiling/replay is intentionally not used for process-interference samples."]))
    except Exception as e:
        return _result("E31", [_case("E31", "single_client_baseline", "INCONCLUSIVE", valid=False, limitations=[f"baseline correctness/measurement failed: {e}"])])

    # Two ordinary CUDA processes, each with an independent context.
    argv = _logic_argv(exe, variant="serial", device=a.device, warmup=5, repeats=30, size=65536, iterations=256)
    context_clients: list[subprocess.Popen[str]] = []
    try:
        context_clients.append(subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=client_env, start_new_session=True))
        context_clients.append(subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=client_env, start_new_session=True))
        p1, p2 = context_clients
        o1, e1 = p1.communicate(timeout=a.case_timeout)
        o2, e2 = p2.communicate(timeout=a.case_timeout)
        pair = [{"returncode": p1.returncode, "stdout": o1, "stderr": e1}, {"returncode": p2.returncode, "stdout": o2, "stderr": e2}]
        _write(out / "two_context_clients.json", pair)
        if any(x["returncode"] != 0 for x in pair):
            raise RuntimeError("one or more separate-context clients exited unsuccessfully")
        nums = [_summarize_native(_parse_native(x["stdout"], "serial"))[0] for x in pair]
        vals = [v for ns in nums for v in ns]
        cases.append(_case("E31", "two_separate_contexts", "GPU_RUN", valid=bool(vals),
            configuration={"device": a.device, "gpu_uuid": lease["selected_uuid"], "clients": 2, "independent_contexts": True},
            metrics={"median_ms": statistics.median(vals), "p95_ms": sorted(vals)[min(len(vals)-1, math.ceil(.95*len(vals))-1)]} if vals else {},
            samples={"client_elapsed_ms": vals}, limitations=["Concurrent client latency is interference-sensitive and is not a scheduler fairness guarantee."]))
    except Exception as e:
        cases.append(_case("E31", "two_separate_contexts", "INCONCLUSIVE", valid=False, limitations=[f"two-context clients failed: {e}"]))
    finally:
        _reap_clients(context_clients)

    # Private server lifecycle. Refuse an existing path; never signal a global server.
    control = _tool("nvidia-cuda-mps-control")
    if not control:
        cases.append(_case("E31", "two_private_mps_clients", "INCONCLUSIVE", valid=False, limitations=["nvidia-cuda-mps-control unavailable"]))
        return _result("E31", cases)
    run_nonce = next(tempfile._get_candidate_names())
    # CUDA MPS puts a Unix-domain socket named "control" under this path.
    # Keep that path short enough for sockaddr_un.sun_path even when the
    # campaign output directory is deeply nested.
    pipe = Path(tempfile.mkdtemp(prefix="atlas-mps-", dir="/tmp"))
    os.chmod(pipe, 0o700)
    logs = out / ("logs-" + run_nonce)
    logs.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(logs, 0o700)
    path_record = {"pipe_directory": str(pipe), "control_socket": str(pipe / "control"),
                   "control_socket_path_bytes": len(os.fsencode(pipe / "control")) + 1,
                   "control_socket_limit_bytes": 108, "pipe_directory_mode": "0700",
                   "pipe_path_origin": "private tempfile.mkdtemp(prefix='atlas-mps-', dir='/tmp')",
                   "logs_directory": str(logs), "logs_directory_mode": "0700",
                   "logs_archive_location": "campaign output directory"}
    _write(out / "mps_path_provenance.json", path_record)
    mps_env = os.environ.copy()
    mps_env["CUDA_MPS_PIPE_DIRECTORY"] = str(pipe)
    mps_env["CUDA_MPS_LOG_DIRECTORY"] = str(logs)
    clients: list[subprocess.Popen[str]] = []
    owned_pids: list[int] = []
    cleanup_error: str | None = None
    start_attempted = False
    start_succeeded = False
    owned_processes_confirmed = False
    try:
        start_attempted = True
        daemon = _run([control, "-d"], timeout=20, env=mps_env)
        _write(out / "mps_start.json", daemon)
        if daemon["returncode"] != 0:
            raise RuntimeError("private MPS daemon start failed: " + (daemon["stderr"] or "unknown error"))
        start_succeeded = True
        time.sleep(1)
        # MPS launches its server lazily on the first CUDA client. A successful
        # private control connection and ownership of the daemon prove startup;
        # an empty server list before clients is expected and is not failure.
        readiness = _mps_control(control, mps_env, "get_server_list")
        owned_pids = _private_mps_pids(pipe)
        if not owned_pids:
            raise RuntimeError("private MPS control socket responded but no daemon process using its pipe was discoverable")
        if not all(_mps_process_matches(pid, pipe) for pid in owned_pids):
            raise RuntimeError("private MPS daemon process did not match the campaign-owned pipe")
        owned_processes_confirmed = True
        _write(out / "mps_readiness.json", {"control_command": "get_server_list",
            "server_list": readiness, "empty_server_list_is_valid_before_clients": True,
            "owned_daemon_pids": owned_pids, "private_pipe": str(pipe)})
        for _ in range(2):
            clients.append(subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=mps_env,
                                             start_new_session=True))
        # Poll only this private control socket while the two clients run. The
        # MPS server PID must appear and each listed PID must retain the exact
        # private pipe in its environment before the measurement is accepted.
        server_poll_started = time.monotonic()
        server_deadline = server_poll_started + min(30.0, max(5.0, a.case_timeout))
        server_polls: list[dict[str, Any]] = []
        pids: list[int] = []
        while time.monotonic() < server_deadline:
            try:
                server_list = _mps_control(control, mps_env, "get_server_list", timeout=3)
                listed = _mps_server_pids(server_list)
                matched = bool(listed) and all(_mps_process_matches(pid, pipe) for pid in listed)
                server_polls.append({"elapsed_s": time.monotonic() - server_poll_started,
                                     "server_list": server_list, "listed_pids": listed,
                                     "all_listed_pids_match_private_pipe": matched})
                if matched:
                    pids = listed
                    owned_pids = sorted(set(owned_pids + listed + _private_mps_pids(pipe)))
                    break
            except Exception as e:
                server_polls.append({"elapsed_s": time.monotonic() - server_poll_started,
                                     "error": f"{type(e).__name__}: {e}"})
            time.sleep(0.25)
        _write(out / "mps_server_polls.json", server_polls)
        if not pids:
            raise RuntimeError("private MPS server PID did not appear with verifiable private-pipe ownership after clients started")
        client_results = []
        deadline = time.monotonic() + a.case_timeout
        for proc in clients:
            remaining = max(.1, deadline - time.monotonic())
            try:
                so, se = proc.communicate(timeout=remaining)
                client_results.append({"returncode": proc.returncode, "stdout": so, "stderr": se})
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.communicate(timeout=5)
                raise RuntimeError("private MPS client timed out and was terminated")
        _write(out / "two_mps_clients.json", client_results)
        if any(c["returncode"] != 0 for c in client_results):
            raise RuntimeError("one or more private MPS clients exited unsuccessfully")
        ns = [_summarize_native(_parse_native(c["stdout"], "serial"))[0] for c in client_results]
        vals = [v for sub in ns for v in sub]
        if not vals:
            raise RuntimeError("private MPS clients returned no valid samples")
        cases.append(_case("E31", "two_private_mps_clients", "GPU_RUN", valid=True,
            configuration={"device": a.device, "gpu_uuid": lease["selected_uuid"], "clients": 2, "private_pipe": str(pipe), "server_pids": pids},
            metrics={"median_ms": statistics.median(vals), "p95_ms": sorted(vals)[min(len(vals)-1, math.ceil(.95*len(vals))-1)]},
            samples={"client_elapsed_ms": vals}, limitations=["Private MPS client timing only; MPS scheduler fairness and fault isolation are not established.", "Counter replay is omitted for concurrent clients."]))
    except Exception as e:
        cases.append(_case("E31", "two_private_mps_clients", "INCONCLUSIVE", valid=False, limitations=[str(e)]))
    finally:
        _reap_clients(locals().get("clients", []))
        # A failed -d may leave no daemon at all. Never send a blind control
        # command: first discover processes whose environment proves this
        # exact private pipe, and only then use its control socket.
        if start_attempted and not owned_processes_confirmed:
            discovered = _private_mps_pids(pipe)
            if discovered and all(_mps_process_matches(pid, pipe) for pid in discovered):
                owned_pids = discovered
                owned_processes_confirmed = True
        if owned_processes_confirmed:
            try:
                _mps_control(control, mps_env, "quit", timeout=10)
            except Exception as e:
                cleanup_error = f"private MPS quit failed: {type(e).__name__}: {e}"
        stop_deadline = time.monotonic() + 10
        while owned_pids and time.monotonic() < stop_deadline:
            owned_pids = [pid for pid in owned_pids if _mps_process_matches(pid, pipe)]
            if not owned_pids:
                break
            time.sleep(.2)
        remaining = _private_mps_pids(pipe)
        if start_succeeded and not owned_processes_confirmed:
            cleanup_error = cleanup_error or "could not confirm ownership and termination of the private MPS daemon/server"
        if owned_pids or remaining:
            cleanup_error = cleanup_error or "campaign-owned MPS daemon/server processes remained after quit timeout"
        if cleanup_error:
            _write(out / "mps_cleanup_error.json", {"error": cleanup_error, "private_pipe_retained": str(pipe),
                                                       "remaining_owned_pids": remaining,
                                                       "path_provenance": path_record})
            path_record["cleanup"] = "retained for diagnosis; process cleanup not proven"
            _write(out / "mps_path_provenance.json", path_record)
            for case in cases:
                if case.get("variant") == "two_private_mps_clients":
                    case["status"] = "INCONCLUSIVE"
                    case["checks"]["valid"] = False
                    case["limitations"].append(cleanup_error)
            if not any(case.get("variant") == "two_private_mps_clients" for case in cases):
                cases.append(_case("E31", "two_private_mps_clients", "INCONCLUSIVE", valid=False,
                                   limitations=[cleanup_error, f"Private control path retained at {pipe}."]))
        else:
            try:
                shutil.rmtree(pipe)
                path_record["cleanup"] = "private pipe directory removed after no owned daemon/server remained"
                _write(out / "mps_path_provenance.json", path_record)
            except OSError as e:
                cleanup_error = f"private pipe cleanup failed: {e}"
                path_record["cleanup"] = f"private pipe directory retained after cleanup error: {e}"
                _write(out / "mps_path_provenance.json", path_record)
                cases.append(_case("E31", "mps_cleanup", "INCONCLUSIVE", valid=False, limitations=[cleanup_error]))
    return _result("E31", cases)


def _telemetry(selector: str) -> dict[str, Any]:
    query = "timestamp,power.draw,clocks.current.sm,clocks.current.memory,temperature.gpu"
    raw = _run(["nvidia-smi", "--query-gpu=" + query, "--format=csv,noheader,nounits", "-i", selector], timeout=5)
    names = ("timestamp", "power_w", "sm_clock_mhz", "memory_clock_mhz", "temperature_c")
    values: dict[str, Any] = {name: None for name in names}
    if raw.get("returncode") == 0:
        rows = list(csv.reader(raw.get("stdout", "").splitlines(), skipinitialspace=True))
        if len(rows) == 1 and len(rows[0]) == len(names):
            values["timestamp"] = rows[0][0].strip() or None
            for index, key in enumerate(names[1:], start=1):
                cell = rows[0][index].strip()
                try:
                    values[key] = float(cell) if cell and cell.lower() not in ("n/a", "na", "not supported") else None
                except ValueError:
                    values[key] = None
        else:
            raw["parse_error"] = f"expected exactly one CSV row with {len(names)} fixed columns"
    raw["values"] = values
    return raw


def _collect_telemetry(selector: str, start: float, stop: threading.Event,
                       target: list[dict[str, Any]]) -> None:
    while not stop.is_set():
        before = time.monotonic()
        raw = _telemetry(selector)
        target.append({"elapsed_s": before - start, "values": raw["values"],
                       "returncode": raw.get("returncode"), "stderr": raw.get("stderr", ""),
                       "parse_error": raw.get("parse_error"), "raw_stdout": raw.get("stdout", "")})
        stop.wait(max(0.0, 1.0 - (time.monotonic() - before)))


def _stable_windows(samples: list[dict[str, Any]]) -> tuple[bool, float | None, float | None, dict[str, Any]]:
    """Find the longest contiguous interval covered only by stable 30 s windows."""
    fields = ("power_w", "sm_clock_mhz", "memory_clock_mhz", "temperature_c")
    records = sorted(samples, key=lambda x: x["elapsed_s"])
    def stable_window(first: int) -> int | None:
        first_t = records[first]["elapsed_s"]
        last = next((j for j in range(first + 1, len(records))
                     if records[j]["elapsed_s"] - first_t >= 30.0), None)
        if last is None:
            return None
        window = records[first:last + 1]
        gaps = [window[i]["elapsed_s"] - window[i - 1]["elapsed_s"] for i in range(1, len(window))]
        if not gaps or max(gaps) > 2.5 or window[-1]["elapsed_s"] - window[0]["elapsed_s"] < 30.0:
            return None
        for key in fields:
            vals = [row["values"].get(key) for row in window]
            if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in vals):
                return None
            span = max(vals) - min(vals)
            if key == "temperature_c" and span > 3.0:
                return None
            if key in ("sm_clock_mhz", "memory_clock_mhz") and span / max(1.0, abs(statistics.mean(vals))) > 0.05:
                return None
            if key == "power_w" and span / max(1.0, abs(statistics.mean(vals))) > 0.10:
                return None
        return last

    best_start: int | None = None
    best_end: int | None = None
    best_count = 0
    for first in range(len(records)):
        cursor = first
        count = 0
        while True:
            last = stable_window(cursor)
            if last is None:
                break
            count += 1
            cursor = last
        if count > best_count:
            best_start, best_end, best_count = first, cursor, count
    if best_count >= 3 and best_start is not None and best_end is not None:
        start_s = records[best_start]["elapsed_s"]
        end_s = records[best_end]["elapsed_s"]
        return True, start_s, end_s, {"stable_window_count": best_count, "window_seconds": 30,
            "maximum_sample_gap_seconds": 2.5,
            "limits": {"power_relative_span": 0.10, "clock_relative_span": 0.05, "temperature_span_c": 3.0},
            "stable_interval_start_s": start_s, "stable_interval_end_s": end_s}
    return False, None, None, {"stable_window_count": best_count, "window_seconds": 30,
        "limits": {"power_relative_span": 0.10, "clock_relative_span": 0.05, "temperature_span_c": 3.0}}


def _integrate_energy(samples: list[dict[str, Any]], start_s: float, end_s: float) -> float | None:
    rows = sorted(samples, key=lambda x: x["elapsed_s"])
    if end_s <= start_s or len(rows) < 2:
        return None
    left = max((i for i, row in enumerate(rows) if row["elapsed_s"] <= start_s), default=None)
    right = next((i for i, row in enumerate(rows) if row["elapsed_s"] >= end_s), None)
    if left is None or right is None or right <= left:
        return None
    selected = rows[left:right + 1]
    points = [(row["elapsed_s"], row["values"].get("power_w")) for row in selected]
    if any(not isinstance(power, (int, float)) or not math.isfinite(power) or power <= 0 for _, power in points):
        return None
    if any(points[i][0] - points[i - 1][0] > 2.5 for i in range(1, len(points))):
        return None

    def power_at(moment: float) -> float | None:
        for (ta, pa), (tb, pb) in zip(points, points[1:]):
            if ta <= moment <= tb:
                fraction = (moment - ta) / (tb - ta)
                return pa + fraction * (pb - pa)
        return None

    left_power = power_at(start_s)
    right_power = power_at(end_s)
    if left_power is None or right_power is None:
        return None
    clipped = [(start_s, left_power)]
    clipped.extend((t, p) for t, p in points if start_s < t < end_s)
    clipped.append((end_s, right_power))
    return sum((clipped[i][1] + clipped[i - 1][1]) * 0.5 * (clipped[i][0] - clipped[i - 1][0])
               for i in range(1, len(clipped)))


def _parse_steady_native(text: str, expected_variant: str, expected_events: int = 30) -> tuple[dict[str, Any], list[float], list[float], list[float], dict[str, int]]:
    """Validate paired event timings and absolute CLOCK_MONOTONIC bounds."""
    try:
        data = json.loads(text)
    except Exception as e:
        raise ValueError(f"native steady output is not JSON: {e}") from e
    if data.get("experiment") != "E03" or data.get("checks", {}).get("valid") is not True:
        raise ValueError("native steady output failed experiment/correctness contract")
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError("native steady output has no cases array")
    matched = [case for case in cases if case.get("variant") == expected_variant]
    if len(matched) != 1:
        raise ValueError(f"native steady output must contain exactly one {expected_variant} case")
    case = matched[0]
    if case.get("status") != "GPU_RUN" or case.get("checks", {}).get("valid") is not True:
        raise ValueError("native steady case is not a valid GPU_RUN")
    samples = case.get("samples", {})
    required = ("event_ms", "host_start_monotonic_s", "host_end_monotonic_s")
    arrays = [samples.get(name) for name in required]
    if any(not isinstance(values, list) for values in arrays):
        raise ValueError("native steady output lacks paired event_ms/host-bound arrays")
    if len({len(values) for values in arrays}) != 1 or len(arrays[0]) < expected_events:
        raise ValueError(f"native steady output must contain at least {expected_events} paired event samples")
    events, starts, ends = ([float(x) for x in values] for values in arrays)
    if any(not math.isfinite(x) or x <= 0 for x in events):
        raise ValueError("native steady event_ms samples must be finite and positive")
    if any(not math.isfinite(x) for x in starts + ends):
        raise ValueError("native steady host timestamps must be finite")
    for i, (start, end, event_ms) in enumerate(zip(starts, ends, events)):
        if start <= 0 or end <= start:
            raise ValueError(f"native steady event {i} has invalid host bounds")
        host_ms = (end - start) * 1000.0
        if event_ms > host_ms * 1.10 + 0.25:
            raise ValueError(f"native steady event {i} CUDA-event time exceeds its host bracket")
        if i and start < ends[i - 1]:
            raise ValueError(f"native steady event {i} overlaps or reorders its prior launch")
    config = case.get("configuration", {})
    clock_value = str(config.get("host_clock_source", ""))
    if clock_value != "CLOCK_MONOTONIC":
        raise ValueError("native steady output does not identify Linux CLOCK_MONOTONIC timestamps")
    configured_duration = config.get("steady_requested_seconds")
    interval_start = config.get("measurement_interval_start_monotonic_s")
    interval_end = config.get("measurement_interval_end_monotonic_s")
    try:
        configured_duration = float(configured_duration)
        interval_start = float(interval_start)
        interval_end = float(interval_end)
    except (TypeError, ValueError):
        raise ValueError("native steady output lacks requested duration or absolute measurement interval bounds")
    if not math.isfinite(configured_duration) or configured_duration <= 0:
        raise ValueError("native steady output has an invalid configured steady duration")
    if not math.isfinite(interval_start) or not math.isfinite(interval_end) or interval_end <= interval_start:
        raise ValueError("native steady output has invalid measurement interval bounds")
    if starts[0] < interval_start - 1e-6 or ends[-1] > interval_end + 1e-6:
        raise ValueError("native event timestamps fall outside its declared measurement interval")
    data["_steady_interval"] = (interval_start, interval_end)
    data["_steady_requested_seconds"] = configured_duration
    data["_validated_case"] = case
    work = _actual_work_contract(data)
    return data, events, starts, ends, work


def _run_e33_resident(a: argparse.Namespace, lease: dict[str, Any], exe: Path,
                      out: Path, schedule_seconds: int) -> dict[str, Any]:
    """Run one resident native process while parent telemetry is sampled."""
    cases: list[dict[str, Any]] = []
    policy_contracts: dict[str, dict[str, int]] = {}
    requested_size, requested_iterations = (1 << 20), 100000
    for variant in ("serial", "interleaved"):
        policy_dir = out / variant
        policy_dir.mkdir(parents=True, exist_ok=True)
        base_args = {"variant": variant, "device": a.device, "requested_size": requested_size,
                     "requested_iterations": requested_iterations, "steady_seconds": schedule_seconds,
                     "resident_process": True}
        # Validate useful output and establish the child-reported work contract
        # before the long resident schedule begins.
        warm_cmd = _logic_argv(exe, variant=variant, device=a.device, warmup=5,
                               repeats=a.repeats, size=requested_size, iterations=requested_iterations)
        warm = _run(warm_cmd, timeout=a.case_timeout, env=os.environ.copy())
        _write(policy_dir / "precondition.json", warm)
        try:
            if warm.get("returncode") != 0:
                raise ValueError("precondition workload exited unsuccessfully")
            warm_native = _parse_native(warm["stdout"], variant, a.repeats)
            warm_work = _actual_work_contract(warm_native)
            policy_contracts[variant] = warm_work
        except Exception as e:
            cases.append(_case("E33", variant, "INCONCLUSIVE", valid=False,
                               configuration={**base_args, "gpu_uuid": lease["selected_uuid"]},
                               limitations=[f"useful-output precondition failed before timing: {e}"]))
            continue

        telemetry: list[dict[str, Any]] = []
        stop = threading.Event()
        started_abs = time.monotonic()
        sampler = threading.Thread(target=_collect_telemetry,
                                   args=(lease["selected_uuid"], started_abs, stop, telemetry), daemon=True)
        sampler.start()
        command = _logic_argv(exe, variant=variant, device=a.device, warmup=5,
                              repeats=a.repeats, size=requested_size, iterations=requested_iterations)
        command.extend(["--steady-seconds", str(schedule_seconds)])
        timeout = min(a.case_timeout, schedule_seconds + 60)
        raw = _run(command, timeout=timeout, env=os.environ.copy())
        ended_abs = time.monotonic()
        stop.set()
        sampler.join(timeout=7)
        _write(policy_dir / "resident_run.json", raw)
        _write(policy_dir / "telemetry.json", telemetry)
        errors: list[str] = []
        native_interval: tuple[float, float] | None = None
        try:
            if raw.get("returncode") != 0 or raw.get("timed_out"):
                raise ValueError(f"resident workload failed (returncode={raw.get('returncode')}, timed_out={raw.get('timed_out')})")
            native, event_ms, host_starts, host_ends, actual_work = _parse_steady_native(raw["stdout"], variant, 30)
            if actual_work != warm_work:
                raise ValueError("resident actual work differs from its validated precondition")
            reported_duration = native["_steady_requested_seconds"]
            if float(reported_duration) != float(schedule_seconds):
                raise ValueError("resident output steady duration differs from the requested schedule")
            interval_start, interval_end = native["_steady_interval"]
            native_interval = (interval_start, interval_end)
            parent_started = started_abs
            parent_ended = ended_abs
            if interval_start < parent_started - 0.05 or interval_end > parent_ended + 0.05:
                raise ValueError("native measurement interval falls outside the parent-monitored process window")
            if host_starts[0] < parent_started - 0.05 or host_ends[-1] > parent_ended + 0.05:
                raise ValueError("native event timestamps fall outside the parent-monitored process window")
            work_units_per_event = actual_work["work_units_per_sample"]
            batch_records = [{"start_s": start - parent_started, "end_s": end - parent_started,
                              "elapsed_ms": elapsed, "work_contract": actual_work,
                              "work_units": work_units_per_event}
                             for elapsed, start, end in zip(event_ms, host_starts, host_ends)]
        except Exception as e:
            errors.append(str(e))
            event_ms, batch_records = [], []
        if sampler.is_alive():
            errors.append("telemetry sampler did not stop within its bounded join timeout")
        stable, stable_start, stable_end, stability = _stable_windows(telemetry)
        stable_events = [batch for batch in batch_records
                         if stable_start is not None and stable_end is not None
                         and batch["start_s"] >= stable_start and batch["end_s"] <= stable_end]
        stable_vals = [float(batch["elapsed_ms"]) for batch in stable_events]
        useful_work = sum(batch["work_units"] for batch in stable_events)
        energy_start = stable_events[0]["start_s"] if stable_events else None
        energy_end = stable_events[-1]["end_s"] if stable_events else None
        energy = _integrate_energy(telemetry, energy_start, energy_end) if stable and energy_start is not None and energy_end is not None else None
        completed = ended_abs - started_abs
        limits = errors[:]
        if not stable:
            limits.append("No three adjacent complete 30-second telemetry windows met the documented power, clock, and temperature bounds during the resident workload.")
        if not stable_events:
            limits.append("No complete native event fell wholly inside the verified contiguous stable telemetry interval.")
        if energy is None:
            limits.append("Energy is unknown: stable power telemetry was unavailable, nonpositive, or had a gap above 2.5 seconds.")
        status = "GPU_RUN" if stable and stable_events and energy is not None and not errors else "INCONCLUSIVE"
        metrics: dict[str, float] = {}
        if stable_vals:
            metrics["median_ms"] = statistics.median(stable_vals)
            metrics["p95_ms"] = sorted(stable_vals)[min(len(stable_vals) - 1, math.ceil(.95 * len(stable_vals)) - 1)]
            metrics["post_stability_work_units"] = float(useful_work)
            resident_event_seconds = sum(stable_vals) / 1000.0
            interval_seconds = max(0.0, (energy_end or 0.0) - (energy_start or 0.0))
            if resident_event_seconds > 0:
                metrics["post_stability_work_units_per_event_s"] = useful_work / resident_event_seconds
            if interval_seconds > 0:
                metrics["post_stability_work_units_per_wall_s"] = useful_work / interval_seconds
        if energy is not None and useful_work > 0:
            metrics["energy_j"] = energy
            metrics["energy_j_per_work_unit"] = energy / useful_work
        case = _case("E33", variant, status, valid=(status == "GPU_RUN"),
            configuration={**base_args, "gpu_uuid": lease["selected_uuid"],
                           "schedule_elapsed_s": completed, "telemetry_sample_period_s": 1.0,
                           "work_unit_definition": "child-reported launched total work units per native event",
                           "actual_work_per_event": policy_contracts.get(variant, {}),
                           "native_event_count": len(event_ms),
                           "native_measurement_interval_start_monotonic_s": native_interval[0] if native_interval else None,
                           "native_measurement_interval_end_monotonic_s": native_interval[1] if native_interval else None,
                           "parent_window_start_monotonic_s": started_abs,
                           "parent_window_end_monotonic_s": ended_abs, "stability": stability,
                           "post_stability_measurement_start_s": energy_start,
                           "post_stability_measurement_end_s": energy_end,
                           "stable_interval_start_s": stable_start, "stable_interval_end_s": stable_end},
            metrics=metrics,
            samples={"event_ms": event_ms,
                     "host_start_monotonic_s": [batch["start_s"] + started_abs for batch in batch_records],
                     "host_end_monotonic_s": [batch["end_s"] + started_abs for batch in batch_records]},
            limitations=limits)
        cases.append(case)
    if len(policy_contracts) == 2 and policy_contracts["serial"] != policy_contracts["interleaved"]:
        reason = "serial and interleaved E03 schedules did not report equal actual work per native event"
        for case in cases:
            case["status"] = "INCONCLUSIVE"
            case["checks"]["valid"] = False
            case["limitations"].append(reason)
    return _result("E33", cases)

def run_e33(a: argparse.Namespace) -> dict[str, Any]:
    ok, why, lease = _lease_ok(a.device)
    exe = a.build_dir / "bin" / "atlas_logic"
    if not ok:
        return _result("E33", [_case("E33", "steady_state", "INCONCLUSIVE", valid=False, limitations=[why])])
    if not exe.is_file():
        return _result("E33", [_case("E33", "steady_state", "INCONCLUSIVE", valid=False, limitations=[f"missing executable: {exe}"])])
    full_steady_run = a.mode == "full" and not a.profile_diagnostic
    if full_steady_run:
        out = a.output_dir / "host" / "E33"
        out.mkdir(parents=True, exist_ok=True)
        return _run_e33_resident(a, lease, exe, out, schedule_seconds=150)
    total_seconds = min(20, max(2, a.smoke_seconds))
    schedule_seconds = total_seconds / 2.0
    requested_size, requested_iterations = ((1 << 20, 100000) if full_steady_run else (65536, 256))
    out = a.output_dir / "host" / "E33"
    out.mkdir(parents=True, exist_ok=True)
    cases = []
    policy_contracts: dict[str, dict[str, int]] = {}
    for variant in ("serial", "interleaved"):
        policy_dir = out / variant
        policy_dir.mkdir(parents=True, exist_ok=True)
        base_args = {"variant": variant, "device": a.device,
                     "requested_size": requested_size, "requested_iterations": requested_iterations}
        # Precondition and validate a complete output before collecting benchmark samples.
        warm_cmd = _logic_argv(exe, variant=variant, device=a.device, warmup=a.warmup,
                               repeats=a.repeats, size=requested_size, iterations=requested_iterations)
        warm_started = time.monotonic()
        warm = _run(warm_cmd, timeout=a.case_timeout, env=os.environ.copy())
        warm_duration = time.monotonic() - warm_started
        _write(policy_dir / "precondition.json", warm)
        try:
            if warm.get("returncode") != 0:
                raise ValueError("precondition workload exited unsuccessfully")
            warm_native = _parse_native(warm["stdout"], variant, a.repeats)
            warm_work = _actual_work_contract(warm_native)
            policy_contracts[variant] = warm_work
        except Exception as e:
            cases.append(_case("E33", variant, "INCONCLUSIVE", valid=False,
                               configuration={**base_args, "gpu_uuid": lease["selected_uuid"]},
                               limitations=[f"useful-output precondition failed before timing: {e}"]))
            continue

        telemetry: list[dict[str, Any]] = []
        stop = threading.Event()
        started = time.monotonic()
        sampler = threading.Thread(target=_collect_telemetry,
                                   args=(lease["selected_uuid"], started, stop, telemetry), daemon=True)
        sampler.start()
        deadline = started + schedule_seconds
        batch_records: list[dict[str, Any]] = []
        errors: list[str] = []
        batch_number = 0
        try:
            while time.monotonic() < deadline:
                batch_start = time.monotonic()
                remaining = deadline - batch_start
                if remaining < max(0.5, warm_duration * 1.5):
                    break
                command = _logic_argv(exe, variant=variant, device=a.device, warmup=0,
                                      repeats=a.repeats, size=requested_size, iterations=requested_iterations)
                timeout = min(a.case_timeout, remaining)
                raw = _run(command, timeout=timeout, env=os.environ.copy())
                batch_end = time.monotonic()
                _write(policy_dir / f"batch_{batch_number:04d}.json", raw)
                batch_number += 1
                try:
                    if raw.get("returncode") != 0:
                        raise ValueError(f"benchmark exited with {raw.get('returncode')}")
                    native = _parse_native(raw["stdout"], variant, a.repeats)
                    vals, _ = _summarize_native(native)
                    actual = _actual_work_contract(native)
                    if actual != warm_work:
                        raise ValueError("measured batch actual work differs from its validated precondition")
                    batch_records.append({"start_s": batch_start - started, "end_s": batch_end - started,
                                          "elapsed_ms": vals, "work_contract": actual,
                                          "work_units": actual["work_units_per_sample"] * len(vals)})
                except Exception as e:
                    errors.append(f"batch {batch_number - 1}: {e}")
                    break
        finally:
            stop.set()
            sampler.join(timeout=7)
        _write(policy_dir / "telemetry.json", telemetry)
        stable, stable_start, stable_end, stability = _stable_windows(telemetry) if full_steady_run else (False, None, None, {})
        if sampler.is_alive():
            errors.append("telemetry sampler did not stop within its bounded join timeout")
        all_vals = [value for batch in batch_records for value in batch["elapsed_ms"]]
        stable_batches = [batch for batch in batch_records
                          if stable_start is not None and stable_end is not None
                          and batch["start_s"] >= stable_start and batch["end_s"] <= stable_end]
        stable_vals = [value for batch in stable_batches for value in batch["elapsed_ms"]]
        all_work_units = sum(batch["work_units"] for batch in batch_records)
        useful_work = sum(batch["work_units"] for batch in stable_batches)
        energy_start = stable_batches[0]["start_s"] if stable_batches else None
        energy_end = stable_batches[-1]["end_s"] if stable_batches else None
        energy = _integrate_energy(telemetry, energy_start, energy_end) if stable and energy_start is not None and energy_end is not None else None
        completed = time.monotonic() - started
        limits = errors[:]
        if a.mode == "smoke":
            limits.append("Smoke mode is a short diagnostic and makes no steady-state claim.")
        if a.profile_diagnostic:
            limits.append("Profiler diagnostic burst only; case disposition remains INCONCLUSIVE and no steady-state claim is made.")
        elif not stable:
            limits.append("No three adjacent complete 30-second telemetry windows met the documented power, clock, and temperature bounds within this schedule interval.")
        if not stable_vals:
            limits.append("No complete validated benchmark batch fit wholly inside the verified contiguous stable telemetry interval.")
        if energy is None:
            limits.append("Energy is unknown: stable power telemetry was unavailable, nonpositive, or had a gap above 2.5 seconds.")
        status = "GPU_RUN" if a.mode == "full" and stable and stable_vals and energy is not None and not errors else "INCONCLUSIVE"
        metrics: dict[str, float] = {}
        measured_vals = stable_vals if stable_vals else all_vals
        if measured_vals:
            metrics["median_ms"] = statistics.median(measured_vals)
            metrics["p95_ms"] = sorted(measured_vals)[min(len(measured_vals) - 1, math.ceil(.95 * len(measured_vals)) - 1)]
        if all_work_units:
            metrics["measured_work_units"] = float(all_work_units)
        if stable_vals:
            metrics["post_stability_work_units"] = float(useful_work)
            kernel_seconds = sum(stable_vals) / 1000.0
            interval_seconds = max(0.0, (energy_end or 0.0) - (energy_start or 0.0))
            if kernel_seconds > 0:
                metrics["post_stability_work_units_per_event_s"] = useful_work / kernel_seconds
            if interval_seconds > 0:
                metrics["post_stability_work_units_per_wall_s"] = useful_work / interval_seconds
        if energy is not None and stable_vals:
            metrics["energy_j"] = energy
            metrics["energy_j_per_work_unit"] = energy / useful_work
        burst_correct = bool(all_vals) and not errors
        case_valid = burst_correct if a.profile_diagnostic else status == "GPU_RUN"
        cases.append(_case("E33", variant, status, valid=case_valid,
            configuration={**base_args, "gpu_uuid": lease["selected_uuid"], "schedule_interval_limit_s": schedule_seconds,
                           "schedule_elapsed_s": completed, "telemetry_sample_period_s": 1.0,
                           "work_unit_definition": "child-reported launched total work units per E03 timing sample",
                           "actual_work_per_sample": policy_contracts.get(variant, {}),
                           "stability": stability, "post_stability_measurement_start_s": energy_start,
                           "post_stability_measurement_end_s": energy_end,
                           "stable_interval_start_s": stable_start, "stable_interval_end_s": stable_end}, metrics=metrics,
            samples={"elapsed_ms": all_vals}, limitations=limits))
    if len(policy_contracts) == 2:
        left = policy_contracts["serial"]
        right = policy_contracts["interleaved"]
        if left != right:
            reason = "serial and interleaved E03 schedules did not report equal actual work per timing sample"
            for case in cases:
                case["status"] = "INCONCLUSIVE"
                case["checks"]["valid"] = False
                case["limitations"].append(reason)
    return _result("E33", cases)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--experiment", required=True, choices=["E00", "E01", "E31", "E33", "E34", "E35", "E36", "E38"])
    p.add_argument("--build-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    p.add_argument("--warmup", type=int, default=5)
    p.add_argument("--repeats", type=int, default=30)
    p.add_argument("--device", type=int, default=0)
    p.add_argument("--case-timeout", type=float, default=300)
    p.add_argument("--smoke-seconds", type=int, default=20)
    p.add_argument("--profile-diagnostic", action="store_true",
                    help="run a short admitted E33 burst for profiling; it never claims steady state")
    a = p.parse_args()
    a.build_dir = a.build_dir.resolve()
    a.output_dir = a.output_dir.resolve()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    runners = {"E00": run_e00, "E01": run_e01, "E31": run_e31, "E33": run_e33,
               "E34": run_e34, "E35": run_e35, "E36": run_e36, "E38": run_e38}
    try:
        result = runners[a.experiment](a)
    except Exception as e:
        result = _result(a.experiment, [_case(a.experiment, "host_stage", "INCONCLUSIVE", valid=False, limitations=[f"host stage error: {type(e).__name__}: {e}"])])
    _write(a.output_dir / "host" / f"{a.experiment}.json", result)
    _emit(result)
    return 0 if result["checks"]["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
