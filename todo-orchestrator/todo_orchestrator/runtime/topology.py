"""Runtime GPU topology discovery without fixed device or cable assumptions."""

from __future__ import annotations

import csv
import io
import re
import subprocess
from collections.abc import Callable


Runner = Callable[[list[str]], str]
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


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
    numa_column: int | None = None
    for raw in topology.splitlines():
        clean = ANSI_ESCAPE.sub("", raw)
        if "\t" in clean:
            fields = [item.strip() for item in clean.split("\t")]
            if fields and not fields[0]:
                fields.pop(0)
        else:
            fields = clean.split()
        if not fields:
            continue
        if len(fields) > 1 and fields[0].startswith("GPU") and fields[1].startswith("GPU"):
            header = fields
            for name in ("NUMA Affinity", "NUMA_Affinity"):
                if name in header:
                    numa_column = header.index(name)
                    break
            continue
        if fields[0].startswith("GPU") and fields[0][3:].isdigit():
            index = int(fields[0][3:])
            gpu_columns = [name for name in header if name.startswith("GPU") and name[3:].isdigit()]
            for name in gpu_columns:
                column = header.index(name) + 1
                if column < len(fields):
                    links.setdefault(index, {})[int(name[3:])] = fields[column]
            if numa_column is not None and numa_column + 1 < len(fields):
                value = fields[numa_column + 1]
                if value.lstrip("-").isdigit():
                    numa[index] = value

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
