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
from pathlib import Path
import subprocess
import sys
import time
import tomllib

SKILLS = Path(__file__).resolve().parents[2]
QUALIFIED_PATHS = (
    "local-coding-worker/local_worker/supervisor.py",
    "todo-orchestrator/todo_orchestrator/background/host.py",
    "todo-orchestrator/todo_orchestrator/runtime/facade.py",
    "cuda/scripts/cuda_controller.py", "local-coding-worker/local_worker/residency.py",
    "local-coding-worker/local_worker/servers/llama_cpp.py",
    "cuda/scripts/qualify_observer_residency.py")
SOURCE_VALIDATION_PATHS = ("tests/as1/test_sk_as1_gpu.py",)
sys.path.insert(0, str(SKILLS / "local-coding-worker"))
sys.path.insert(0, str(SKILLS / "todo-orchestrator"))
sys.path.insert(0, str(SKILLS / "cuda/scripts"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, document):
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def foreground_check():
    # The controller supplies the exact CUDA_VISIBLE_DEVICES and lease receipt.
    visible = os.environ["CUDA_VISIBLE_DEVICES"].split(",")
    receipt = json.loads(Path(os.environ["TODO_GPU_LEASE_RECEIPT"]).read_text())
    assert set(receipt["resource_ids"]) == {f"accelerator:{gpu}" for gpu in visible}
    from local_worker.residency import observe_residency
    admission_observation = observe_residency(visible)
    library = ctypes.CDLL(os.environ.get("CUDA_RUNTIME_LIBRARY", "libcudart.so"))
    library.cudaMalloc.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_size_t]
    library.cudaFree.argtypes = [ctypes.c_void_p]
    library.cudaMemset.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t]
    library.cudaMemcpy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    count = ctypes.c_int()
    assert library.cudaGetDeviceCount(ctypes.byref(count)) == 0 and count.value == len(visible)
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
    print(json.dumps({"checked_gpu_uuids": visible, "allocation_bytes_per_device": 1024 * 1024,
                      "lease": receipt, "admission_observation": admission_observation,
                      "device_memset_copy_verified": True}))


def qualify(args):
    from local_worker.canonical_runtime import bind, validate, subprocess_environment
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
    identity, context = bind(args.project)
    validate(identity)
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    profile = tomllib.loads((SKILLS / "local-coding-worker/config/production-profile.toml").read_text())
    profile["deployment_policy"].update(allowed_gpu_uuids=selected, max_real_workers=1)
    backend = ProductionBackend(args.project, service_state_root=args.output / "supervisor", profile=profile)
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
                          "isolate_nvlink_domain": False, "isolate_pcie_root": False},
            "argv": [sys.executable, str(Path(__file__).resolve()), "--foreground-check"],
            "paths": [], "recipe": "baseline", "preempt_grace_seconds": 30,
            "timeout": 60, "_storage_root": str(args.output / "controller")}
        spec_path = args.output / "controller-spec.json"
        write(spec_path, spec)
        controller_process = subprocess.Popen([sys.executable, str(SKILLS / "cuda/scripts/cuda_controller.py"),
            "run", "--spec", str(spec_path), "--json"], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env={**os.environ, **subprocess_environment(identity)})
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
        for kind, document in documents.items():
            write(args.output / f"{kind}.json", document)
    if documents["cleanup"]["remaining_slots"]:
        raise RuntimeError("owned physical cleanup incomplete; retain lease and investigate")
    receipt = {"format": "sk-as1-gpu-hardware/1", "source_identity": {
        "skills_root": str(source_root), "installed_skills_root": str(SKILLS),
        "source_commit": source_commit, "runtime_context": context,
        "runtime_identity": identity.public(), "sha256": {**hashes, **source_only_hashes},
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
    parser.add_argument("--gpu-uuid", action="append", required=True)
    qualify(parser.parse_args())


if __name__ == "__main__":
    main()
