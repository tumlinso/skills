"""Runtime GPU topology discovery without fixed device or cable assumptions."""

from __future__ import annotations

import csv
import io
import subprocess
from collections.abc import Callable


Runner = Callable[[list[str]], str]


def _run(argv: list[str]) -> str:
    return subprocess.run(argv, text=True, capture_output=True, check=True).stdout


def discover_gpu_topology(runner: Runner = _run) -> list[dict[str, object]]:
    inventory = runner([
        "nvidia-smi", "--query-gpu=index,uuid,pci.bus_id", "--format=csv,noheader,nounits",
    ])
    topology = runner(["nvidia-smi", "topo", "-m"])
    devices: dict[int, dict[str, str]] = {}
    for row in csv.reader(io.StringIO(inventory)):
        if len(row) >= 3:
            index = int(row[0].strip())
            devices[index] = {"uuid": row[1].strip(), "pci_bus_id": row[2].strip()}

    links: dict[int, dict[int, str]] = {index: {} for index in devices}
    numa: dict[int, str] = {}
    header: list[str] = []
    for raw in topology.splitlines():
        fields = raw.split()
        if not fields:
            continue
        if len(fields) > 1 and fields[0].startswith("GPU") and fields[1].startswith("GPU"):
            header = fields
            continue
        if fields[0].startswith("GPU") and fields[0][3:].isdigit():
            index = int(fields[0][3:])
            gpu_columns = [name for name in header if name.startswith("GPU") and name[3:].isdigit()]
            for offset, name in enumerate(gpu_columns, start=1):
                if offset < len(fields):
                    links.setdefault(index, {})[int(name[3:])] = fields[offset]
            if "NUMA Affinity" in raw:
                # nvidia-smi keeps NUMA affinity as the penultimate numeric column.
                numeric = [value for value in fields[len(gpu_columns) + 1:] if value.lstrip("-").isdigit()]
                if numeric:
                    numa[index] = numeric[-1]

    parent = {index: index for index in devices}

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    for left, adjacent in links.items():
        for right, relation in adjacent.items():
            if relation.startswith("NV") and right in devices:
                union(left, right)
    groups: dict[int, list[int]] = {}
    for index in devices:
        groups.setdefault(find(index), []).append(index)

    resources: list[dict[str, object]] = []
    for index, device in sorted(devices.items()):
        domain = device["pci_bus_id"].split(":", 1)[0]
        numa_node = numa.get(index, "unknown")
        island = "-".join(str(item) for item in sorted(groups[find(index)]))
        resources.append({
            "id": f"accelerator:{device['uuid']}",
            "kind": "accelerator",
            "tags": {
                "index": str(index),
                "uuid": device["uuid"],
                "pci_bus_id": device["pci_bus_id"],
                "numa_node": numa_node,
                "pcie_root": f"{domain}:numa:{numa_node}",
                "nvlink_domain": f"runtime:{island}",
            },
            "enabled": True,
        })
    return resources
