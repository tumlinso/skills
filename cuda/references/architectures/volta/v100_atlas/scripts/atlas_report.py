#!/usr/bin/env python3
"""Render evidence-gated benchmark comparisons from a campaign directory."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
        return float(value)
    return None


def raw_median(case: dict[str, Any], metric: str, sample: str) -> tuple[float | None, int]:
    value = number(case.get("metrics", {}).get(metric))
    values = case.get("samples", {}).get(sample, [])
    clean = [number(v) for v in values if number(v) is not None] if isinstance(values, list) else []
    if value is None and clean:
        value = statistics.median(clean)
    return value, len(clean)


def raw_p95(case: dict[str, Any], metric: str, sample: str) -> float | None:
    value = number(case.get("metrics", {}).get(metric))
    values = case.get("samples", {}).get(sample, [])
    clean = sorted(number(v) for v in values if number(v) is not None) if isinstance(values, list) else []
    if value is not None:
        return value
    return clean[min(len(clean) - 1, int(0.95 * (len(clean) - 1)))] if clean else None


def valid(case: dict[str, Any]) -> bool:
    return case.get("status") == "GPU_RUN" and case.get("checks", {}).get("valid") is True


def axes(case: dict[str, Any]) -> tuple[str, str, str]:
    config = case.get("configuration", {})
    return (str(config.get("size", "?")), str(config.get("reuse", "?")),
            str(config.get("pattern", "?")))


def artifact_link(run_dir: Path, experiment: str, profile: str) -> str:
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    for item in results.get(experiment, {}).get("raw_artifacts", []):
        text = str(item)
        if f"{experiment}-{profile}-" in text and text.endswith("/artifacts"):
            candidate = Path(text) / profile / "run"
            report_name = "report.nsys-rep" if profile == "nsys" else "report.ncu-rep"
            report_path = run_dir / candidate / report_name
            if report_path.is_file() and report_path.stat().st_size:
                return (candidate / report_name).as_posix()
    return ""


def profile_rows(results: dict[str, Any], run_dir: Path) -> tuple[list[str], list[dict[str, Any]]]:
    lines = ["## Profiler evidence", "", "Each entry below is backed by a validated receipt. Nsys supplies timeline evidence; NCU replay supplies kernel counters and is not used for throughput.", ""]
    records: list[dict[str, Any]] = []
    found = 0
    for experiment in sorted(results):
        for case in results[experiment].get("samples", []):
            profiles = case.get("profiles", {})
            if not isinstance(profiles, dict):
                continue
            for recipe, evidence in profiles.items():
                if not isinstance(evidence, dict):
                    continue
                summary = evidence.get("summary", {})
                link = artifact_link(run_dir, experiment, recipe)
                if recipe == "nsys":
                    tops = summary.get("top_kernels", []) if isinstance(summary, dict) else []
                    hints = summary.get("bottleneck_hints", []) if isinstance(summary, dict) else []
                    signal = "GPU activity present=" + str(evidence.get("trace_has_gpu_work"))
                    counts = evidence.get("sqlite_activity_counts", {})
                    if isinstance(counts, dict):
                        signal += (f"; SQLite kernel rows={counts.get('kernels', 0)}, "
                                   f"memcpy rows={counts.get('memcpy', 0)}, memset rows={counts.get('memset', 0)}")
                    if evidence.get("gpu_memtime_rows"):
                        signal += f", GPU copy rows={evidence['gpu_memtime_rows']}"
                else:
                    tops = summary.get("top_kernels", []) if isinstance(summary, dict) else []
                    hot = summary.get("hot_kernel", {}) if isinstance(summary, dict) else {}
                    hints = [hot.get("class")] if isinstance(hot, dict) and hot.get("class") else []
                    signal = "counter_valid=" + str(evidence.get("counter_valid"))
                if not link:
                    link = str(evidence.get("report", ""))
                lines.append(f"- **{experiment} / {case.get('variant', 'case')} / {recipe}:** {signal}; analysis status `{summary.get('status', 'unknown')}`. "
                             + (f"[raw report]({link})" if link else "raw report path unavailable"))
                if recipe == "nsys" and summary.get("measurement_scope"):
                    lines.append(f"  - Timeline evidence scope: `{summary['measurement_scope']}`; throughput remains sourced from the unprofiled benchmark samples.")
                for row in tops[:3] if isinstance(tops, list) else []:
                    if not isinstance(row, dict):
                        continue
                    name = row.get("name", "<unnamed>")
                    if recipe == "nsys":
                        detail = f"{row.get('instances', '?')} instances, average {row.get('avg_us', '?')} us"
                    else:
                        detail = f"class {row.get('class', '?')}, share {row.get('share_pct', '?')}%"
                    lines.append(f"  - Hot kernel: `{name}` ({detail}).")
                if hints:
                    lines.append("  - Reported hints: " + ", ".join(f"`{x}`" for x in hints if x) + ".")
                profile_valid = (evidence.get("trace_has_gpu_work") is True if recipe == "nsys" else
                                 evidence.get("counter_valid") is True if recipe == "ncu" else False)
                records.append({"experiment": experiment, "variant": case.get("variant"),
                                "recipe": recipe, "valid": profile_valid,
                                "summary_status": summary.get("status"), "raw_report": link,
                                "activity_counts": evidence.get("sqlite_activity_counts"),
                                "measurement_scope": summary.get("measurement_scope"),
                                "top_kernels": tops[:3] if isinstance(tops, list) else [], "hints": hints})
                found += 1
    if not found:
        lines.append("No profiler capture passed receipt validation in this run.")
    lines.append("")
    return lines, records


def composition_analysis(results: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    lines = ["## E39 complete-path representation comparison", "",
             "Rows require correctness-passing GPU cases. A ratio is shown only when both native and candidate cases passed for the same size, reuse count, and input pattern. Full path includes the module's stated transfers and encode/decode work; device allocation remains outside the timed path.", "",
             "| Size | Reuse | Pattern | Seed | Partial group | Variant | Resident median ms | Full-path median ms | Full-path p95 ms | Full/resident | N |", "|---:|---:|---|---:|---:|---|---:|---:|---:|---:|---:|"]
    cases = results.get("E39", {}).get("samples", [])
    grouped: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        size, reuse, pattern = axes(case)
        grouped.setdefault((size, reuse, pattern), {})[str(case.get("variant", "?"))] = case
    ratios: list[dict[str, Any]] = []
    observations = 0
    for key in sorted(grouped, key=lambda x: tuple(int(v) if v.isdigit() else v for v in x[:2]) + (x[2],)):
        variants = grouped[key]
        native = variants.get("native")
        native_full, _ = raw_median(native or {}, "full_path_median_ms", "full_path_ms")
        for variant in ("native", "bitplane", "nibble512"):
            case = variants.get(variant)
            if not case:
                continue
            config = case.get("configuration", {})
            seed = config.get("seed", "?")
            partial_group = config.get("partial_group", "?")
            if not valid(case):
                lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {seed} | {partial_group} | {variant} | — | — | — | — | 0 |")
                continue
            resident, _ = raw_median(case, "resident_compute_median_ms", "resident_compute_ms")
            full, n = raw_median(case, "full_path_median_ms", "full_path_ms")
            p95 = raw_p95(case, "full_path_p95_ms", "full_path_ms")
            ratio = (full / resident) if full is not None and resident and resident > 0 else None
            p95_text = f"{p95:.6g}" if p95 is not None else "—"
            lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {seed} | {partial_group} | {variant} | {resident:.6g} | {full:.6g} | {p95_text} | {ratio:.3g} | {n} |"
                         if resident is not None and full is not None else
                         f"| {key[0]} | {key[1]} | {key[2]} | {seed} | {partial_group} | {variant} | — | — | — | — | {n} |")
            observations += 1
            if variant != "native" and full is not None and native_full is not None and valid(native or {}):
                ratios.append({"size": key[0], "reuse": key[1], "pattern": key[2], "variant": variant,
                               "native_full_path_ms": native_full, "candidate_full_path_ms": full,
                               "native_over_candidate": native_full / full if full > 0 else None,
                               "candidate_wins": full < native_full})
    crossovers: dict[str, Any] = {}
    for variant in ("bitplane", "nibble512"):
        found = [r for r in ratios if r["variant"] == variant and r["candidate_wins"]]
        crossovers[variant] = found[0] if found else None
    if not observations:
        reason = "; ".join(results.get("E39", {}).get("limitations", [])[:2]) or "No GPU cases are available."
        lines += [f"No comparable E39 timing was available. {reason}", "No representation speedup or crossover is claimed."]
    else:
        lines += ["", "Observed first full-path crossover by representation:"]
        for variant, point in crossovers.items():
            if point:
                lines.append(f"- `{variant}` first beat native at size {point['size']}, reuse {point['reuse']}, pattern `{point['pattern']}` ({point['native_over_candidate']:.3g}× native/candidate time).")
            else:
                lines.append(f"- `{variant}`: no full-path crossover observed in valid matched cases.")
    lines.append("")
    return lines, {"valid_case_count": observations, "matched_comparisons": ratios, "first_crossovers": crossovers}


def tensor_analysis(results: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    lines = ["## E11 tensor versus bitset complete path", "",
             "Comparisons require a correctness-passing packed AND+POPC baseline and candidate at the same tested universe. Ratios are baseline/candidate; encoding, transfer, kernel, and materialization follow each case's `complete_path_contract`.", "",
             "| Universe | Variant | Full-path median ms | Packed baseline ms | Baseline/candidate | N |", "|---:|---|---:|---:|---:|---:|"]
    cases = results.get("E11", {}).get("samples", [])
    by_universe: dict[str, dict[str, dict[str, Any]]] = {}
    for case in cases:
        universe = str(case.get("configuration", {}).get("universe", "?"))
        by_universe.setdefault(universe, {})[str(case.get("variant"))] = case
    comparisons: list[dict[str, Any]] = []
    rows = 0
    for universe, variants in sorted(by_universe.items(), key=lambda item: int(item[0]) if item[0].isdigit() else 0):
        baseline = variants.get("packed_and_popc")
        baseline_ms, _ = raw_median(baseline or {}, "full_path_median_ms", "full_path_ms")
        baseline_ok = baseline is not None and valid(baseline) and baseline_ms is not None
        for variant in ("packed_and_popc", "dp4a", "fp16_wmma"):
            case = variants.get(variant)
            if not case:
                continue
            full, n = raw_median(case, "full_path_median_ms", "full_path_ms")
            if not valid(case) or full is None:
                lines.append(f"| {universe} | {variant} | — | {baseline_ms:.6g} | — | 0 |" if baseline_ms is not None else
                             f"| {universe} | {variant} | — | — | — | 0 |")
                continue
            ratio = baseline_ms / full if baseline_ok and full > 0 else None
            lines.append(f"| {universe} | {variant} | {full:.6g} | {baseline_ms:.6g} | {ratio:.3g} | {n} |"
                         if baseline_ms is not None and ratio is not None else
                         f"| {universe} | {variant} | {full:.6g} | — | — | {n} |")
            rows += 1
            if variant != "packed_and_popc" and baseline_ok:
                comparisons.append({"universe": universe, "variant": variant,
                                    "packed_baseline_ms": baseline_ms, "candidate_ms": full,
                                    "baseline_over_candidate": ratio, "candidate_wins": full < baseline_ms})
    if not rows:
        reason = "; ".join(results.get("E11", {}).get("limitations", [])[:2]) or "No GPU cases are available."
        lines += [f"No E11 full-path comparison was available. {reason}", "No tensor or DP4A speedup is claimed without a valid packed baseline."]
    lines.append("")
    return lines, {"valid_case_count": rows, "matched_comparisons": comparisons}


def transport_analysis(results: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    lines = ["## E20 directed peer transfer rates", "",
             "Rates are payload GB/s from validated cases; bidirectional aggregates include two payload directions. They do not prove physical link routing.", "",
             "| Source | Destination | Bytes | Direction | Payload GB/s | Valid |", "|---:|---:|---:|---|---:|---:|"]
    rows: list[dict[str, Any]] = []
    for case in results.get("E20", {}).get("samples", []):
        config, metrics = case.get("configuration", {}), case.get("metrics", {})
        src = config.get("source", config.get("device_a", "?"))
        dst = config.get("destination", config.get("device_b", "?"))
        size = config.get("bytes", config.get("bytes_per_direction", "?"))
        if case.get("variant") == "directed_peer_copy_one_way":
            rate = number(metrics.get("payload_GB_per_s")); direction = "one-way"
        elif case.get("variant") == "directed_peer_copy_bidirectional":
            rate = number(metrics.get("aggregate_payload_GB_per_s")); direction = "bidirectional aggregate"
        else:
            continue
        ok = valid(case) and rate is not None
        lines.append(f"| {src} | {dst} | {size} | {direction} | {rate:.6g} | {ok} |" if rate is not None else
                     f"| {src} | {dst} | {size} | {direction} | — | False |")
        rows.append({"source": src, "destination": dst, "bytes": size, "direction": direction,
                     "payload_GB_per_s": rate if ok else None, "valid": ok})
    if not rows:
        reason = "; ".join(results.get("E20", {}).get("limitations", [])[:2]) or "No GPU cases are available."
        lines += [f"No directed transfer rates were measured. {reason}", "No bandwidth or topology claim is made."]
    lines.append("")
    return lines, {"directed_rates": rows}


def captured_host_diagnostics(run_dir: Path) -> list[dict[str, Any]]:
    diagnostics = []
    for path in sorted((run_dir / "controller").glob("*/artifacts/foreground.stdout.txt")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        experiment = payload.get("experiment")
        for case in payload.get("cases", []):
            if case.get("status") != "GPU_RUN" and case.get("checks", {}).get("valid") is False:
                diagnostics.append({"experiment": experiment, "case": case, "path": path.relative_to(run_dir).as_posix()})
    return diagnostics


def concise_error(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if "undefined reference" in line or "error:" in line or "Error " in line:
            return line[-500:]
    return lines[-1][-500:] if lines else "No compiler failure text recorded."


def render(run_dir: Path) -> tuple[str, dict[str, Any]]:
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    build = json.loads((run_dir / "build.json").read_text(encoding="utf-8")) if (run_dir / "build.json").exists() else {}
    selected = config.get("experiments", sorted(results))
    lines = ["# V100 benchmark campaign evidence", "",
             f"Run `{run_dir.name}` · mode `{config.get('mode', 'unknown')}` · campaign key `{config.get('campaign_key', 'unknown')}`.", "",
             f"Campaign complete: **{summary.get('complete', False)}**; selected scope complete: **{summary.get('selected_complete', False)}**.", ""]
    counts = summary.get("counts", {})
    lines.append("Disposition counts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ".")
    correctness = summary.get("correctness", {})
    lines.append(f"Correctness: {len(correctness.get('passed', []))} passed, {len(correctness.get('failed', []))} failed, {len(correctness.get('unknown_or_not_run', []))} unknown/not run. Do not read this as an aggregate pass when any item is unknown or failed.")
    if build.get("build", {}).get("returncode") != 0:
        err = build.get("build", {}).get("stderr", "")
        lines += ["", f"**Build gate failed** (return code {build.get('build', {}).get('returncode')}). Root cause: `{concise_error(err)}`. [Build receipt](build.json). No dependent GPU timing or profiler result is credited."]
    if summary.get("completion_blockers"):
        lines += ["", "Campaign blockers:"]
        for item in summary["completion_blockers"][:24]:
            lines.append(f"- {item}")
        if len(summary["completion_blockers"]) > 24:
            lines.append(f"- …and {len(summary['completion_blockers']) - 24} more; see `summary.json`.")
    lines.append("")

    e39_lines, e39_data = composition_analysis(results)
    e11_lines, e11_data = tensor_analysis(results)
    e20_lines, e20_data = transport_analysis(results)
    profile_lines, profiles = profile_rows(results, run_dir)
    lines.extend(e39_lines + e11_lines + e20_lines + profile_lines)

    lines += ["## Host diagnostics", ""]
    diagnostics = captured_host_diagnostics(run_dir)
    for item in diagnostics:
        case = item["case"]
        detail = "; ".join(case.get("limitations", [])) or "case failed its check without a limitation message"
        lines.append(f"- **{item['experiment']} / {case.get('variant', 'case')}** `{case.get('status')}`: {detail}. [Captured JSON]({item['path']})")
    if not diagnostics:
        lines.append("No failed host diagnostic case was found in the archived controller stdout receipts.")
    e36 = results.get("E36", {})
    e36_case = next((c for c in e36.get("samples", []) if c.get("experiment") == "E36"), None)
    if e36_case:
        detail = "; ".join(e36_case.get("limitations", []))
        lines.append(f"- E36 toolchain qualification: `{e36_case.get('status')}` — {detail}.")
    lines += ["", "## E00–E39 dispositions", "",
              "These links point to the original protocol writeups and preserve their authoring provenance; measured evidence is recorded separately in this run's results and raw artifacts.", "",
              "| Experiment | Status | Correctness | Cases | First limitation |", "|---|---|---|---:|---|"]
    for i in range(40):
        experiment = f"E{i:02d}"
        result = results.get(experiment, {})
        first = result.get("limitations", [])
        valid_state = result.get("correctness", {}).get("valid")
        lines.append(f"| [{experiment}](../../experiments/{experiment}.md) | {result.get('status', 'MISSING')} | {valid_state if valid_state is not None else 'unknown'} | {len(result.get('samples', []))} | {(first[0][:180] if first else '—').replace('|', '\\|')} |")
    lines += ["", "Structured evidence: [results.json](results.json), [run_config.json](run_config.json), [summary.json](summary.json).", ""]
    analysis = {"campaign_key": config.get("campaign_key"), "complete": summary.get("complete", False),
                "selected_complete": summary.get("selected_complete", False), "correctness": correctness,
                "e39": e39_data, "e11": e11_data, "e20": e20_data, "profiles": profiles,
                "host_diagnostics": diagnostics}
    return "\n".join(lines), analysis


def write_report(run_dir: Path) -> dict[str, Any]:
    markdown, analysis = render(run_dir)
    (run_dir / "REPORT.md").write_text(markdown, encoding="utf-8")
    (run_dir / "analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return analysis


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    analysis = write_report(run_dir)
    print(json.dumps({"run_dir": str(run_dir), "report": str(run_dir / "REPORT.md"),
                      "analysis": str(run_dir / "analysis.json"), "complete": analysis["complete"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
