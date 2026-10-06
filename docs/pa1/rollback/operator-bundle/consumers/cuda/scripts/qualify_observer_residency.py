#!/usr/bin/env python3
"""Explicit hardware qualification of the installed observer production path.

Requires root-supplied approval and an independently validated installation.
Never downloads models, mutates services, or chooses a fallback GPU island.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
import tomllib
import uuid

SKILLS = Path(__file__).resolve().parents[2]
QUALIFIED_PATHS = (
    "todo-orchestrator/todo_orchestrator/background/host.py",
    "todo-orchestrator/todo_orchestrator/runtime/facade.py",
    "cuda/scripts/cuda_controller.py",
    "cuda/scripts/qualify_observer_residency.py")
SOURCE_VALIDATION_PATHS = ("tests/as1/test_sk_as1_gpu.py", "tests/as1/test_sk_as1_gpu_host_guards.py")
sys.path.insert(0, str(SKILLS / "todo-orchestrator"))
sys.path.insert(0, str(SKILLS / "cuda/scripts"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, document):
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)



def normalize_pci_bus_id(value):
    """Canonicalize the documented hexadecimal domain:bus:device.function form."""
    match = re.fullmatch(r"([0-9a-fA-F]{1,8}):([0-9a-fA-F]{1,2}):([0-9a-fA-F]{1,2})\.([0-7])", value)
    if not match:
        raise ValueError("malformed PCI bus ID")
    domain, bus, device, function = (int(part, 16) for part in match.groups())
    if device > 31:
        raise ValueError("invalid PCI device number")
    return f"{domain:08x}:{bus:02x}:{device:02x}.{function:x}"


def map_runtime_devices(pci_ids, rows, expected_uuids, visible):
    """Fail closed before allocation unless physical PCI/UUID/index order agrees."""
    if len(pci_ids) != len(expected_uuids) or len(visible) != len(expected_uuids):
        raise ValueError("runtime/lease device count mismatch")
    if len(set(expected_uuids)) != len(expected_uuids) or len(set(visible)) != len(visible):
        raise ValueError("duplicate lease or visible device")
    by_pci, seen_uuids = {}, set()
    for row in rows:
        device_uuid = row["uuid"]
        if not re.fullmatch(r"GPU-[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", device_uuid):
            raise ValueError("physical GPU UUID required; MIG mapping unsupported")
        key = normalize_pci_bus_id(row["pci_bus_id"])
        if key in by_pci or device_uuid in seen_uuids:
            raise ValueError("ambiguous physical PCI/UUID mapping")
        seen_uuids.add(device_uuid)
        by_pci[key] = row
    mapped = []
    for logical, pci_id in enumerate(pci_ids):
        row = by_pci.get(normalize_pci_bus_id(pci_id))
        if row is None or row["uuid"] != expected_uuids[logical]:
            raise ValueError("runtime physical UUID order differs from approved lease")
        if row["mig_mode"] not in ("Disabled", "N/A", "[N/A]"):
            raise ValueError("MIG physical-device mapping unsupported")
        if visible[logical] not in (str(row["index"]), row["uuid"]):
            raise ValueError("controller visible-device order differs from physical mapping")
        mapped.append(row["uuid"])
    return mapped


def bind_cuda_runtime(library):
    # cudaDeviceGetPCIBusId(char*, int, int), CUDA Runtime API 12.0 DEVICE docs.
    signatures = {
        "cudaRuntimeGetVersion": [ctypes.POINTER(ctypes.c_int)],
        "cudaGetDeviceCount": [ctypes.POINTER(ctypes.c_int)],
        "cudaDeviceGetPCIBusId": [ctypes.POINTER(ctypes.c_char), ctypes.c_int, ctypes.c_int],
        "cudaSetDevice": [ctypes.c_int],
        "cudaMalloc": [ctypes.POINTER(ctypes.c_void_p), ctypes.c_size_t],
        "cudaFree": [ctypes.c_void_p],
        "cudaMemset": [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t],
        "cudaMemcpy": [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int],
        "cudaDeviceSynchronize": [],
    }
    for name, args in signatures.items():
        function = getattr(library, name)  # Resolve ALL required symbols before any CUDA call.
        function.argtypes = args
        function.restype = ctypes.c_int
    return library


def foreground_check():
    if not __debug__:
        raise RuntimeError("qualification requires enabled runtime checks")
    from project_control.runtime_binding import bind_local_runtime
    bind_local_runtime()
    # The controller supplies the exact CUDA_VISIBLE_DEVICES and lease receipt.
    visible = os.environ["CUDA_VISIBLE_DEVICES"].split(",")
    receipt = json.loads(Path(os.environ["TODO_GPU_LEASE_RECEIPT"]).read_text())
    expected_uuids = [resource.removeprefix("accelerator:") for resource in receipt["resource_ids"]]
    from local_worker.residency import observe_residency
    admission_observation = observe_residency(expected_uuids)
    library_path = Path(os.environ["CUDA_RUNTIME_LIBRARY"]).resolve(strict=True)
    library_sha = digest(library_path)
    assert library_sha == os.environ["CUDA_RUNTIME_LIBRARY_SHA256"]
    library = bind_cuda_runtime(ctypes.CDLL(str(library_path)))
    version = ctypes.c_int()
    assert library.cudaRuntimeGetVersion(ctypes.byref(version)) == 0 and version.value >= 12000
    count = ctypes.c_int()
    assert library.cudaGetDeviceCount(ctypes.byref(count)) == 0 and count.value == len(visible)
    runtime_pci_ids = []
    for device in range(count.value):
        pci_id = ctypes.create_string_buffer(32)
        assert library.cudaDeviceGetPCIBusId(pci_id, len(pci_id), device) == 0
        runtime_pci_ids.append(pci_id.value.decode("ascii"))
    pci_observed_unix = time.time()
    pci_query = subprocess.run(["nvidia-smi", "--query-gpu=uuid,pci.bus_id,index,mig.mode.current",
                                "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True)
    pci_rows = []
    for line in pci_query.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) != 4:
            raise ValueError("malformed physical GPU PCI observation")
        pci_rows.append({"uuid": fields[0], "pci_bus_id": fields[1], "index": int(fields[2]), "mig_mode": fields[3]})
    mapped_uuids = map_runtime_devices(runtime_pci_ids, pci_rows, expected_uuids, visible)
    for device in range(count.value):
        pointer = ctypes.c_void_p()
        assert library.cudaSetDevice(device) == 0
        assert library.cudaMalloc(ctypes.byref(pointer), 1024 * 1024) == 0
        try:
            assert library.cudaMemset(pointer, 0x5A, 1024 * 1024) == 0
            assert library.cudaDeviceSynchronize() == 0
            observed = (ctypes.c_ubyte * 32)()
            assert library.cudaMemcpy(observed, pointer, 32, 2) == 0
            assert bytes(observed) == b"\x5a" * 32
        finally:
            assert library.cudaFree(pointer) == 0
    print(json.dumps({"checked_gpu_uuids": mapped_uuids, "allocation_bytes_per_device": 1024 * 1024,
                      "controller_visible_devices": visible,
                      "lease": receipt, "admission_observation": admission_observation,
                      "runtime_gpu_uuids": mapped_uuids,
                      "runtime_pci_bus_ids": runtime_pci_ids,
                      "physical_pci_observation": {"observed_unix": pci_observed_unix, "devices": pci_rows},
                      "cuda_runtime": {"path": str(library_path), "sha256": library_sha, "version": version.value},
                      "device_memset_copy_verified": True}))


def qualify(args):
    from project_control.runtime_binding import bind_local_runtime
    receiver_identity = bind_local_runtime()
    from todo_orchestrator.runtime_identity import (
        bind_canonical_runtime, validate_runtime, controlled_subprocess_env,
        project_runtime_context)
    from local_worker.supervisor import ProductionBackend
    from local_worker.residency import observe_residency
    from cuda_controller import probe_gpus, text_run, compute_processes
    from todo_orchestrator.background.store import BackgroundStore

    approval = json.loads(args.approval.read_text())
    selected = sorted(set(args.gpu_uuid))
    resource_ids = [f"accelerator:{gpu}" for gpu in selected]
    if len(selected) != 2 or sorted(approval.get("resource_ids", [])) != resource_ids:
        raise ValueError("approval must identify exactly the requested two physical GPU UUIDs")
    if approval.get("authorized") is not True:
        raise ValueError("explicit root authorization required")
    source_root = args.source_root.resolve(strict=True)
    hashes = {path: digest(SKILLS / path) for path in QUALIFIED_PATHS}
    if any(digest(source_root / path) != hashes[path] for path in QUALIFIED_PATHS):
        raise ValueError("installed candidate differs from approved current source")
    source_only_hashes = {path: digest(source_root / path) for path in SOURCE_VALIDATION_PATHS}
    source_commit = subprocess.run(["git", "-C", str(source_root), "rev-parse", "HEAD"],
                                  capture_output=True, text=True, check=True).stdout.strip()
    todo_identity = bind_canonical_runtime()
    validate_runtime(todo_identity)
    try:
        context = project_runtime_context(args.project, todo_identity)
    except Exception as error:
        if getattr(error, "code", None) != "project_not_bootstrapped":
            raise
        context = todo_identity.public()
    private_state = args.private_state_root.resolve()
    if any(private_state.is_relative_to(root.resolve()) for root in (source_root, SKILLS, args.project, args.output)):
        raise ValueError("private residency state must remain outside all source and artifact roots")
    if private_state.exists():
        raise ValueError("qualification private state root must be new; preserve existing recovery markers")
    library_path = args.cuda_runtime_library.resolve(strict=True)
    if digest(library_path) != args.cuda_runtime_sha256:
        raise ValueError("root-approved CUDA runtime hash mismatch")
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    profile = tomllib.loads((receiver_identity.root / "config/production-profile.toml").read_text())
    profile["deployment_policy"].update(allowed_gpu_uuids=selected, max_real_workers=1)
    backend = ProductionBackend(args.project, service_state_root=private_state, profile=profile)
    documents = {"approval": approval, "discovery": {
        "devices": probe_gpus(dynamic=True), "approved_gpu_uuids": selected,
        "topology": text_run(["nvidia-smi", "topo", "-m"]).stdout}}
    first = reloaded = reused = None
    unrelated_before = sorted((row["uuid"], row["pid"], row["process"]) for row in compute_processes()
                              if row["uuid"] not in selected)
    controller_process = None
    def turn(session):
        answer = backend.run_observer_turn({"format": "PC-LOCAL-INVESTIGATOR-TURN/2",
            "session_id": session["service_lease_id"], "compute_profile": "narrow",
            "messages": [{"role": "user", "content": "Reply with the word ready."}],
            "max_tokens": 24, "timeout_seconds": 90})
        if answer.get("status") != "available" or not answer.get("text", "").strip():
            raise RuntimeError(f"real observer turn failed: {answer}")
        return answer
    try:
        first = backend.warm(compute_profile="narrow")
        if sorted(first["gpu_uuids"]) != selected:
            raise RuntimeError("production allocation exceeded approved UUIDs")
        initial_turn = turn(first)
        backend.release(first["service_lease_id"])
        spec = {"schema_version": 1, "project_root": str(args.project),
            "resources": {"gpu_uuids": selected, "gpus": 2,
                          "cpu_threads": 0, "ram_bytes": 0,
                          "isolate_nvlink_domain": False, "isolate_pcie_root": False},
            "argv": [sys.executable, str(Path(__file__).resolve()), "--foreground-check"],
            "paths": [], "recipe": "baseline", "preempt_grace_seconds": 30,
            "timeout": 60, "_storage_root": str(args.output / "controller")}
        spec_path = args.output / "controller-spec.json"
        write(spec_path, spec)
        controller_environment = {**os.environ, **controlled_subprocess_env(todo_identity)}
        controller_process = subprocess.Popen([sys.executable, str(SKILLS / "cuda/scripts/cuda_controller.py"),
            "run", "--spec", str(spec_path), "--json"], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env={**controller_environment,
                "CUDA_RUNTIME_LIBRARY": str(library_path), "CUDA_RUNTIME_LIBRARY_SHA256": args.cuda_runtime_sha256})
        deadline = time.monotonic() + 120
        while controller_process.poll() is None and time.monotonic() < deadline:
            backend.poll()
            time.sleep(0.1)
        if controller_process.poll() is None:
            raise RuntimeError("foreground controller deadline exceeded")
        stdout, stderr = controller_process.communicate()
        result = json.loads(stdout)
        if controller_process.returncode != 0 or result.get("ok") is not True:
            raise RuntimeError(f"foreground controller failed: {result}, {stderr[-1000:]}")
        lease = json.loads(Path(result["lease_receipt"]).read_text())
        evidence = BackgroundStore(args.output / "controller").result(result["evidence_id"])
        documents["controller"] = {"spec": spec, "result": result, "lease": lease, "evidence": evidence}
        documents["foreground"] = json.loads(Path(result["stdout_path"]).read_text())
        if not backend.cleanup_receipts:
            raise RuntimeError("observer eviction not observed")
        documents["quiescence"] = {"eviction": backend.cleanup_receipts[-1],
            "controller": evidence["summary"]["resource_samples"]["quiescence"]}
        reloaded = backend.warm(compute_profile="narrow")
        reload_turn = turn(reloaded)
        backend.release(reloaded["service_lease_id"])
        reused = backend.warm(compute_profile="narrow")
        reuse_turn = turn(reused)
        backend.release(reused["service_lease_id"])
        documents["reuse"] = {"before": reloaded, "after": reused, "reused": reused["reused"],
            "initial_evicted_endpoint": first,
            "first_turn": initial_turn, "reload_turn": reload_turn, "reuse_turn": reuse_turn}
    finally:
        if controller_process is not None and controller_process.poll() is None:
            controller_process.terminate()
            controller_process.wait(timeout=15)
        deadline = time.monotonic() + 30
        while not backend.evict()["quiescent"] and time.monotonic() < deadline:
            time.sleep(0.1)
        documents["cleanup"] = {"receipts": backend.cleanup_receipts,
            "remaining_slots": list(backend._slots),
            "remaining_owned_leases": list(backend._leases),
            "owned_model_pids": [slot.endpoint_descriptor["server_pid"] for slot in backend._slots.values()],
            "unrelated_before": unrelated_before,
            "unrelated_after": sorted((row["uuid"], row["pid"], row["process"]) for row in compute_processes()
                                      if row["uuid"] not in selected),
            "observation": observe_residency(selected)}
        owned_ids = {endpoint["owner_id"] for endpoint in (first, reloaded, reused) if endpoint}
        if "controller" in documents:
            owned_ids.add(documents["controller"]["lease"]["owner_id"])
        documents["cleanup"]["host_owners"] = [
            {"owner_id": owner_id, "state": owner["state"], "resources": owner["resources"]}
            for owner_id in sorted(owned_ids) if (owner := backend.runtime.host.owner(owner_id))]
        documents["cleanup"]["remaining_model_cache_leases"] = [
            str(path.relative_to(private_state)) for path in (private_state / "model-leases").rglob("*.json")]
        for kind, document in documents.items():
            write(args.output / f"{kind}.json", document)
    cleanup = documents["cleanup"]
    if (cleanup["remaining_slots"] or cleanup["remaining_model_cache_leases"] or
            len(cleanup["host_owners"]) != len(owned_ids) or
            any(owner["state"] != "released" or owner["resources"] for owner in cleanup["host_owners"])):
        raise RuntimeError("owned physical cleanup incomplete; retain lease and investigate")
    receipt = {"format": "sk-as1-gpu-hardware/1", "source_identity": {
        "skills_root": str(source_root), "installed_skills_root": str(SKILLS),
        "source_commit": source_commit, "runtime_context": context,
        "runtime_identity": todo_identity.public(),
        "project_control_receiver": {"root": str(receiver_identity.root),
            "manifest_sha256": receiver_identity.manifest_sha256,
            "fingerprint": receiver_identity.fingerprint,
            "file_count": receiver_identity.file_count},
        "sha256": {**hashes, **source_only_hashes},
        "installed_runtime_sha256": hashes, "source_validation_sha256": source_only_hashes},
        **documents, "artifacts": [{"kind": kind, "path": f"{kind}.json",
            "sha256": digest(args.output / f"{kind}.json")} for kind in documents]}
    write(args.output / "receipt.json", receipt)


def main():
    if sys.argv[1:] == ["--foreground-check"]:
        foreground_check()
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-state-root", type=Path, required=True)
    parser.add_argument("--cuda-runtime-library", type=Path, required=True)
    parser.add_argument("--cuda-runtime-sha256", required=True)
    parser.add_argument("--gpu-uuid", action="append", required=True)
    qualify(parser.parse_args())


if __name__ == "__main__":
    main()
