#!/usr/bin/env python3
"""Print an architecture router and remind the agent to inspect its evidence.

This compatibility CLI does not infer bottlenecks or select a workload route.
The model reads the authored architecture guide, considers the supplied
summaries, and chooses the next reference from that evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ARCH_ROUTE_MAP = {
    "volta": "references/architectures/volta/router.md",
    "ampere": "references/architectures/ampere/router.md",
    "hopper": "references/architectures/hopper/router.md",
    "blackwell": "references/architectures/blackwell/router.md",
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
    """Load a supplied compact summary; its claims remain agent-interpreted."""
    if path is None:
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"summary must contain a JSON object: {path}")
    return value


def pick_route(
    benchmark: dict | None,
    nsys: dict | None,
    ncu: dict | None,
) -> tuple[str, str]:
    """Keep the old callable surface while returning no inferred sub-route."""
    del benchmark, nsys, ncu
    return (
        "agent-review",
        "Read the authored architecture router and supplied evidence; the "
        "agent chooses the focused next reference.",
    )


def summarize_evidence(
    benchmark: dict | None,
    nsys: dict | None,
    ncu: dict | None,
) -> list[dict[str, object]]:
    """Retain compact evidence provenance without deciding its implication."""
    result = []
    for label, summary in (("benchmark", benchmark), ("nsys", nsys), ("ncu", ncu)):
        if summary is None:
            continue
        item: dict[str, object] = {"source": label}
        for key in (
            "status", "measurement_scope", "steady_state_timing_valid",
            "trace_valid", "counter_valid", "timing_valid", "needs_rerun_for_timing",
        ):
            if key in summary:
                item[key] = summary[key]
        for key in ("reasons", "notes"):
            values = summary.get(key)
            if isinstance(values, list) and values:
                item[key] = [str(value) for value in values[:3]]
        if summary.get("next_step"):
            item["next_step"] = str(summary["next_step"])
        result.append(item)
    return result


def main() -> int:
    args = parse_args()
    # Parse every explicitly supplied summary so malformed evidence is not
    # silently ignored, but do not rank or interpret its fields here.
    benchmark = load_json(args.benchmark)
    nsys = load_json(args.nsys)
    ncu = load_json(args.ncu)
    route, reason = pick_route(benchmark, nsys, ncu)
    reference = ARCH_ROUTE_MAP[args.arch]
    payload = {
        "arch": args.arch,
        "recommended_route": route,
        "recommended_reference": reference,
        "reason": reason,
        "evidence": summarize_evidence(benchmark, nsys, ncu),
    }
    text = "\n".join(
        [
            f"arch: {payload['arch']}",
            f"recommended_route: {payload['recommended_route']}",
            f"recommended_reference: {payload['recommended_reference']}",
            f"reason: {payload['reason']}",
            *[
                f"evidence[{item['source']}]: " + json.dumps(
                    {key: value for key, value in item.items() if key != "source"},
                    ensure_ascii=False,
                )
                for item in payload["evidence"]
            ],
        ]
    ) + "\n"
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
