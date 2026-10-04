"""Read-only physical observations; ownership remains in the host interlock."""
from __future__ import annotations

import subprocess
import os
from pathlib import Path
import signal
import time


def process_identity(pid: int) -> dict:
    """Identity strong enough to reject PID reuse before signaling a child."""
    stat = (Path("/proc") / str(pid) / "stat").read_text()
    fields = stat[stat.rfind(")") + 2:].split()
    return {"pid": pid, "process_start": fields[19], "process_group": int(fields[2]),
            "executable": str((Path("/proc") / str(pid) / "exe").resolve(strict=True)),
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}


def terminate_owned(identity: dict, *, timeout: float = 10) -> None:
    if identity["boot_id"] != Path("/proc/sys/kernel/random/boot_id").read_text().strip():
        raise ValueError("owned_process_boot_mismatch")
    if not (Path("/proc") / str(identity["pid"])).exists():
        return
    if process_identity(identity["pid"]) != identity or identity["process_group"] != identity["pid"]:
        raise ValueError("owned_process_identity_mismatch")
    for sig in (signal.SIGTERM, signal.SIGKILL):
        os.killpg(identity["process_group"], sig)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                # Reap a direct orphan child when this process is its parent;
                # otherwise /proc disappearance is the wait observation.
                try:
                    waited, _ = os.waitpid(identity["pid"], os.WNOHANG)
                    if waited == identity["pid"]:
                        return
                except ChildProcessError:
                    pass
                current = process_identity(identity["pid"])
            except FileNotFoundError:
                return
            if current != identity:
                raise ValueError("owned_process_identity_changed")
            time.sleep(0.05)
    raise ValueError("owned_process_wait_failed")


def observe_residency(uuids: list[str]) -> dict:
    try:
        devices = subprocess.run(
            ["nvidia-smi", "--query-gpu=uuid,memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, check=True)
        processes = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, check=True)
        selected = set(uuids)
        rows = []
        for line in devices.stdout.splitlines():
            gpu, memory = (part.strip() for part in line.split(","))
            if gpu in selected:
                rows.append({"uuid": gpu, "memory_used_mib": float(memory)})
        apps = []
        for line in processes.stdout.splitlines():
            gpu, pid = (part.strip() for part in line.split(","))
            if gpu in selected:
                apps.append({"uuid": gpu, "pid": int(pid)})
        return {"available": {r["uuid"] for r in rows} == selected,
                "devices": rows, "processes": apps}
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return {"available": False, "devices": [], "processes": [], "reason": str(error)[:300]}


def memory_snapshot(observation: dict, uuids: list[str]) -> dict[str, float]:
    if observation.get("available") is not True:
        raise ValueError("residency_observation_unavailable")
    memory = {row["uuid"]: float(row["memory_used_mib"]) for row in observation["devices"]}
    if set(memory) != set(uuids):
        raise ValueError("residency_observation_incomplete")
    return memory
