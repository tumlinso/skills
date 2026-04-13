from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EASY = "easy to port"
RESTRUCTURE = "possible with restructuring"
POOR = "poor OpenACC target"


def load_candidates(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict) and isinstance(data.get("candidates"), list):
        candidates = data["candidates"]
    else:
        raise ValueError("Candidate input must be a JSON list or an object with a 'candidates' list.")
    return [normalize_candidate(candidate) for candidate in candidates]


def normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    normalized.setdefault("id", candidate.get("name", "candidate"))
    normalized.setdefault("location", "unknown")
    normalized.setdefault("loop_shape", "regular")
    normalized.setdefault("trip_count", "unknown")
    normalized.setdefault("notes", "")
    return normalized


def bool_flag(candidate: dict[str, Any], key: str) -> bool:
    value = candidate.get(key, False)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def classify_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    directives: list[str] = []
    risks: list[str] = []

    loop_shape = str(candidate.get("loop_shape", "regular")).strip().lower()
    branchiness = str(candidate.get("branchiness", "low")).strip().lower()
    trip_count = str(candidate.get("trip_count", "unknown")).strip().lower()
    collapse_depth = int(candidate.get("collapse_depth", 1) or 1)

    pointer_heavy = bool_flag(candidate, "pointer_heavy")
    pointer_chasing = bool_flag(candidate, "pointer_chasing")
    indirect_indexing = bool_flag(candidate, "indirect_indexing")
    gather_scatter = bool_flag(candidate, "gather_scatter")
    loop_dependencies = bool_flag(candidate, "loop_dependencies")
    transfer_dominated = bool_flag(candidate, "transfer_dominated")
    tiny_loop = bool_flag(candidate, "tiny_loop")
    aliasing = bool_flag(candidate, "aliasing_risk")
    ownership = bool_flag(candidate, "ownership_ambiguity")
    hidden_temporaries = bool_flag(candidate, "hidden_temporaries")
    allocation_churn = bool_flag(candidate, "allocation_churn")
    reduction = bool_flag(candidate, "reduction")
    scan = bool_flag(candidate, "scan")
    stable_data_region = bool_flag(candidate, "stable_data_region")
    async_candidate = bool_flag(candidate, "async_candidate")
    function_calls = bool_flag(candidate, "function_calls")
    compute_dense = bool_flag(candidate, "compute_dense")

    if pointer_heavy or pointer_chasing:
        blockers.append("pointer-heavy or pointer-chasing access")
    if indirect_indexing:
        blockers.append("indirect indexing")
    if gather_scatter:
        blockers.append("gather/scatter pattern")
    if loop_dependencies:
        blockers.append("loop-carried dependencies")
    if aliasing:
        blockers.append("aliasing risk")
    if ownership:
        blockers.append("ownership ambiguity")
    if hidden_temporaries:
        blockers.append("hidden temporaries")
    if allocation_churn:
        blockers.append("allocation churn")
    if scan:
        blockers.append("scan or prefix dependency")
    if transfer_dominated:
        blockers.append("transfer-dominated region")
    if tiny_loop:
        blockers.append("tiny loop body")
    if branchiness == "high":
        blockers.append("high branchiness")
    if function_calls:
        risks.append("helper-call boundaries may force transfers or device-compatibility cleanup")
    if loop_shape == "cpu-cache-oriented":
        risks.append("loop order appears CPU-cache-oriented rather than accelerator-shaped")
    if not stable_data_region:
        risks.append("data residency boundary is not yet stable")

    poor_target = False
    if pointer_heavy or pointer_chasing or loop_dependencies or transfer_dominated:
        poor_target = True
    if tiny_loop and not stable_data_region:
        poor_target = True
    if branchiness == "high" and (indirect_indexing or gather_scatter or aliasing):
        poor_target = True

    if poor_target:
        classification = POOR
    elif any(
        [
            indirect_indexing,
            gather_scatter,
            aliasing,
            ownership,
            hidden_temporaries,
            allocation_churn,
            scan,
            branchiness == "medium",
            function_calls,
            loop_shape == "cpu-cache-oriented",
        ]
    ):
        classification = RESTRUCTURE
    else:
        classification = EASY

    if classification != POOR:
        if function_calls and not compute_dense:
            directives.append("kernels")
        else:
            directives.append("parallel loop")
        if collapse_depth > 1:
            directives.append(f"collapse({collapse_depth})")
        if reduction:
            directives.append("reduction")
        if async_candidate and stable_data_region and not transfer_dominated:
            directives.append("async")

    data_region_notes: list[str] = []
    if stable_data_region:
        data_region_notes.append("Prefer one wider data region across adjacent hot loops or calls.")
    else:
        data_region_notes.append("Clarify ownership before committing to a wide data region.")
    if allocation_churn:
        data_region_notes.append("Hoist allocations or scratch setup out of the offloaded region.")
    if function_calls:
        data_region_notes.append("Review helper boundaries for accidental enter/exit churn.")
    if transfer_dominated or tiny_loop:
        data_region_notes.append("A data region alone may not repay the transfer overhead here.")

    return {
        "id": candidate["id"],
        "location": candidate["location"],
        "classification": classification,
        "blockers": dedupe(blockers),
        "suggested_directives": directives,
        "data_region_notes": data_region_notes,
        "risks": dedupe(risks),
        "notes": candidate.get("notes", ""),
        "trip_count": trip_count,
    }


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def summarize_candidates(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = [classify_candidate(candidate) for candidate in candidates]
    counts = {EASY: 0, RESTRUCTURE: 0, POOR: 0}
    blockers: list[str] = []
    directives: list[str] = []
    for summary in summaries:
        counts[summary["classification"]] += 1
        blockers.extend(summary["blockers"])
        directives.extend(summary["suggested_directives"])
    return {
        "counts": counts,
        "candidates": summaries,
        "shared_blockers": dedupe(blockers),
        "directive_families": dedupe(directives),
    }


def render_candidate_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"### {summary['id']}",
        f"- location: {summary['location']}",
        f"- classification: {summary['classification']}",
        f"- suggested directives: {', '.join(summary['suggested_directives']) or 'none'}",
        f"- blockers: {', '.join(summary['blockers']) or 'none'}",
    ]
    if summary["data_region_notes"]:
        lines.append(f"- data-region notes: {' '.join(summary['data_region_notes'])}")
    if summary["risks"]:
        lines.append(f"- risks: {', '.join(summary['risks'])}")
    if summary["notes"]:
        lines.append(f"- notes: {summary['notes']}")
    return "\n".join(lines)


def render_markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# OpenACC Candidate Summary",
        "",
        "## Counts",
        f"- {EASY}: {summary['counts'][EASY]}",
        f"- {RESTRUCTURE}: {summary['counts'][RESTRUCTURE]}",
        f"- {POOR}: {summary['counts'][POOR]}",
        "",
        "## Shared Blockers",
    ]
    if summary["shared_blockers"]:
        lines.extend([f"- {item}" for item in summary["shared_blockers"]])
    else:
        lines.append("- none")
    lines.extend(["", "## Candidates"])
    for candidate in summary["candidates"]:
        lines.extend(["", render_candidate_markdown(candidate)])
    return "\n".join(lines) + "\n"


def render_review_markdown(scope: str, summary: dict[str, Any]) -> str:
    easy = [candidate for candidate in summary["candidates"] if candidate["classification"] == EASY]
    restructure = [candidate for candidate in summary["candidates"] if candidate["classification"] == RESTRUCTURE]
    poor = [candidate for candidate in summary["candidates"] if candidate["classification"] == POOR]
    candidate_rows = ["| Region | Location | Classification | Notes |", "| --- | --- | --- | --- |"]
    for candidate in summary["candidates"]:
        notes = "; ".join(candidate["blockers"][:2]) or "review-backed candidate"
        candidate_rows.append(
            f"| {candidate['id']} | {candidate['location']} | {candidate['classification']} | {notes} |"
        )

    staged_plan: list[str] = []
    if easy:
        staged_plan.append(
            f"1. Port `{easy[0]['id']}` first with the smallest correct data region and verify CPU-equivalent behavior."
        )
    else:
        staged_plan.append("1. No clean first-pass region was found. Fix the leading blocker before offloading.")
    if restructure:
        staged_plan.append(
            f"2. Revisit `{restructure[0]['id']}` after the local restructuring blockers are removed."
        )
    else:
        staged_plan.append("2. Keep the second phase narrow unless new review findings uncover another safe region.")
    if poor:
        staged_plan.append(
            f"3. Leave `{poor[0]['id']}` or the other poor targets on the CPU path until the algorithm or data movement story changes."
        )
    else:
        staged_plan.append("3. Reject broader ports until the first region is correct and measured.")

    lines = [
        "# OpenACC Review",
        "",
        "## Scope",
        scope,
        "",
        "## Candidate Regions",
        *candidate_rows,
        "",
        "## Classification",
        f"- {EASY}: {summary['counts'][EASY]}",
        f"- {RESTRUCTURE}: {summary['counts'][RESTRUCTURE]}",
        f"- {POOR}: {summary['counts'][POOR]}",
        "",
        "## Blockers",
    ]
    if summary["shared_blockers"]:
        lines.extend([f"- {item}" for item in summary["shared_blockers"]])
    else:
        lines.append("- No shared blockers were recorded in the candidate notes.")
    lines.extend(
        [
            "",
            "## Proposed Data-Region Plan",
            "- Keep data resident across adjacent useful work instead of wrapping each tiny loop separately.",
            "- Stabilize ownership and helper boundaries before widening the data region.",
            "- Hoist allocations and short-lived temporaries out of the offloaded steady-state path.",
            "",
            "## Likely Directives / Strategy",
            f"- Candidate directive families: {', '.join(summary['directive_families']) or 'none yet'}",
            "- Prefer the most conservative directive set that keeps the first port correct.",
            "- Delay `async` until overlap is real and the dependency story is stable.",
            "",
            "## Staged Implementation Plan",
            *staged_plan,
            "",
            "## Validation Checklist",
            "- Rebuild the existing CPU path and keep it passing before widening the port.",
            "- Compare the first offloaded region against the CPU baseline on representative and edge-case inputs.",
            "- Re-run correctness checks after each directive or data-region change.",
            "- Only make performance claims after correctness is stable.",
            "",
            "## Performance Risks",
            "- Hidden transfers at helper boundaries may erase any kernel-side gain.",
            "- CPU-cache-oriented loop structure may need layout or ordering changes before offload pays off.",
            "- Irregular indexing, scans, and gather/scatter patterns can underperform even when compilation succeeds.",
            "",
            "## Benchmark Follow-On",
            "- Compare the CPU baseline and OpenACC port under one shared scenario contract.",
            "- Keep correctness or equivalence explicit in the benchmark notes.",
            "- Use compact summaries first and inspect raw profiler artifacts only if the summaries remain inconclusive.",
        ]
    )
    return "\n".join(lines) + "\n"
