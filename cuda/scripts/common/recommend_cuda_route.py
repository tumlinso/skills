#!/usr/bin/env python3
"""Map compact CUDA summaries to one narrow next route."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ARCH_ROUTE_MAP = {
    "volta": {
        "native": "references/architectures/volta/routes/native.md",
        "fusion": "references/architectures/volta/routes/fusion.md",
        "graphs": "references/architectures/volta/routes/fusion.md",
        "hot-kernel": "references/architectures/volta/routes/hot-kernel.md",
        "tensor": "references/architectures/volta/routes/tensor.md",
        "library": "references/common/compute-libraries.md",
        "pipeline": "references/addendum-host-device-pipeline.md",
        "profile": "references/v100_profiling_interpretation.md",
        "rerun": "references/architectures/volta/routes/benchmark.md",
    },
    "ampere": {
        "native": "references/architectures/ampere/programming-guide.md",
        "fusion": "references/architectures/ampere/addendum-kernel-mechanics.md",
        "graphs": "references/architectures/ampere/addendum-kernel-mechanics.md",
        "hot-kernel": "references/architectures/ampere/addendum-kernel-roofline-lab.md",
        "tensor": "references/architectures/ampere/addendum-tensor-core-routing.md",
        "library": "references/common/compute-libraries.md",
        "pipeline": "references/architectures/ampere/addendum-host-device-pipeline.md",
        "profile": "references/architectures/ampere/profiling-interpretation.md",
        "rerun": "references/architectures/ampere/profiling-interpretation.md",
    },
    "hopper": {
        "native": "references/architectures/hopper/programming-guide.md",
        "fusion": "references/architectures/hopper/addendum-kernel-mechanics.md",
        "graphs": "references/architectures/hopper/addendum-kernel-mechanics.md",
        "hot-kernel": "references/architectures/hopper/addendum-kernel-roofline-lab.md",
        "tensor": "references/architectures/hopper/addendum-tensor-core-routing.md",
        "library": "references/common/compute-libraries.md",
        "pipeline": "references/architectures/hopper/addendum-host-device-pipeline.md",
        "profile": "references/architectures/hopper/profiling-interpretation.md",
        "rerun": "references/architectures/hopper/profiling-interpretation.md",
    },
    "blackwell": {
        "native": "references/architectures/blackwell/programming-guide.md",
        "fusion": "references/architectures/blackwell/addendum-kernel-mechanics.md",
        "graphs": "references/architectures/blackwell/addendum-kernel-mechanics.md",
        "hot-kernel": "references/architectures/blackwell/addendum-kernel-roofline-lab.md",
        "tensor": "references/architectures/blackwell/addendum-tensor-core-routing.md",
        "library": "references/common/compute-libraries.md",
        "pipeline": "references/architectures/blackwell/addendum-host-device-pipeline.md",
        "profile": "references/architectures/blackwell/profiling-interpretation.md",
        "rerun": "references/architectures/blackwell/profiling-interpretation.md",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", required=True, choices=sorted(ARCH_ROUTE_MAP))
    parser.add_argument("--nsys", type=Path, default=None)
    parser.add_argument("--ncu", type=Path, default=None)
    parser.add_argument("--benchmark", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    return parser.parse_args()


def load_json(path: Path | None) -> dict | None:
    if path is None:
        return None
    return json.loads(path.read_text())


def pick_route(benchmark: dict | None, nsys: dict | None, ncu: dict | None) -> tuple[str, str]:
    for item in (benchmark, nsys, ncu):
        if item and item.get("status") == "rerun":
            return "rerun", "At least one summary says the measurement must be rerun."
    if benchmark and benchmark.get("recommended_route"):
        route = str(benchmark["recommended_route"])
        if route in {"pipeline", "fusion", "graphs", "hot-kernel", "tensor", "library", "profile", "rerun"}:
            return route, str(benchmark.get("recommended_route_reason", "Benchmark summary chose the route."))
    if nsys and nsys.get("recommended_route"):
        route = str(nsys["recommended_route"])
        if route in {"pipeline", "fusion", "graphs", "hot-kernel", "library", "rerun"}:
            return route, str(nsys.get("recommended_route_reason", "Timeline summary chose the route."))
    if ncu and ncu.get("recommended_route"):
        route = str(ncu["recommended_route"])
        if route in {"fusion", "tensor", "library", "hot-kernel", "profile"}:
            return route, str(ncu.get("recommended_route_reason", "Kernel summary chose the route."))
    if benchmark and benchmark.get("workload_balance") == "transfer-dominant":
        return "pipeline", "Benchmark balance says transfer or staging dominates."
    return "native", "No narrower summary-driven route beat the default architecture path."


def main() -> int:
    args = parse_args()
    benchmark = load_json(args.benchmark)
    nsys = load_json(args.nsys)
    ncu = load_json(args.ncu)
    route, reason = pick_route(benchmark, nsys, ncu)
    reference = ARCH_ROUTE_MAP[args.arch][route]
    payload = {
        "arch": args.arch,
        "recommended_route": route,
        "recommended_reference": reference,
        "reason": reason,
    }
    text = "\n".join(
        [
            f"arch: {payload['arch']}",
            f"recommended_route: {payload['recommended_route']}",
            f"recommended_reference: {payload['recommended_reference']}",
            f"reason: {payload['reason']}",
        ]
    ) + "\n"
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
