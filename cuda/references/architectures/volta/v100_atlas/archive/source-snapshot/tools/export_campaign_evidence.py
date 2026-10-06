#!/usr/bin/env python3
"""Export compact, portable per-experiment summaries from one completed run."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "benchmark_runs/v100-20261006T145155Z-4bd01216"
DEFAULT_OUT = ROOT / "experiments/evidence/v100-20261006"
SOURCE_COMMIT = "f223c51dcfacab602e9bc68b3e65cc75730dc7f8"
ARCHIVE_COMMIT = "5c1f805db80a81f7476ede8292abba69821d104f"
CAMPAIGN_KEY = "7beacfbd95e0d2b8f9725c7ba1477122f16bc1eb686a6a7c94dbf6c7e266794b"
REPOSITORY = "tumlinso/gpu_circuit_bending_atlas"
ARRAY_COUNT_KEY = "raw_sample_counts"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact_case(case: dict) -> dict:
    """Keep case metadata and replace raw vectors with their exact lengths."""
    result = copy.deepcopy(case)
    vectors = result.pop("samples", {})
    counts = {}
    if isinstance(vectors, dict):
        for key, values in vectors.items():
            if isinstance(values, list):
                counts[key] = len(values)
            else:
                counts[key] = None
    result[ARRAY_COUNT_KEY] = counts
    return result


def extract_original_protocol_body(text: str) -> str:
    """Return the frozen Question-through-Record portion of a protocol card."""
    start = re.search(r"(?m)^\*\*Question:\*\*.*(?:\n|$)", text)
    if start is None:
        raise ValueError("protocol card has no Question heading")
    end = re.search(r"(?m)^\*\*Record:\*\*.*(?:\n|$)", text[start.start():])
    if end is None:
        raise ValueError("protocol card has no Record heading")
    return text[start.start():start.start() + end.end()]


def validate_campaign_identity(config: dict, summary: dict, audit: dict, acceptance: dict) -> None:
    """Fail closed unless all campaign sources describe the fixed accepted run."""
    keys = {config.get("campaign_key"), summary.get("campaign_key"), audit.get("campaign_key")}
    if keys != {CAMPAIGN_KEY}:
        raise ValueError("campaign key does not match the accepted measurement campaign")
    if acceptance.get("source_commit") != SOURCE_COMMIT:
        raise ValueError("final acceptance source commit does not match the accepted campaign")
    if not acceptance.get("summary_complete") or acceptance.get("blockers"):
        raise ValueError("final acceptance does not confirm a complete, unblocked campaign")
    uncertainty = acceptance.get("e39_apparent_crossover_uncertainty", {})
    if uncertainty.get("method") != "unpaired bootstrap median difference, 10000 resamples":
        raise ValueError("E39 uncertainty method differs from final acceptance")
    if uncertainty.get("confidence") != 0.95 or uncertainty.get("established_crossover") is not False:
        raise ValueError("E39 uncertainty result differs from final acceptance")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    out_dir = args.out_dir.resolve()
    if not run_dir.is_dir():
        parser.error(f"campaign directory does not exist: {run_dir}")

    filenames = ("results.json", "run_config.json", "build.json", "summary.json",
                 "offline/final-acceptance.json", "offline/measurement-audit.json")
    inputs = {name: run_dir / name for name in filenames}
    missing = [str(p) for p in inputs.values() if not p.is_file()]
    if missing:
        parser.error("missing campaign inputs: " + ", ".join(missing))
    results = json.loads(inputs["results.json"].read_text(encoding="utf-8"))
    config = json.loads(inputs["run_config.json"].read_text(encoding="utf-8"))
    summary = json.loads(inputs["summary.json"].read_text(encoding="utf-8"))
    acceptance = json.loads(inputs["offline/final-acceptance.json"].read_text(encoding="utf-8"))
    audit = json.loads(inputs["offline/measurement-audit.json"].read_text(encoding="utf-8"))
    if not re.fullmatch(r"[0-9a-f]{64}", config.get("campaign_key", "")):
        parser.error("run_config.json has no valid campaign key")
    try:
        validate_campaign_identity(config, summary, audit, acceptance)
    except ValueError as exc:
        parser.error(str(exc))
    if not summary.get("complete") or not summary.get("selected_complete"):
        parser.error("campaign is not complete; refusing to export")
    build = json.loads(inputs["build.json"].read_text(encoding="utf-8"))
    if build.get("build", {}).get("returncode") != 0:
        parser.error("build receipt does not show a successful CUDA build")
    if set(results) != {f"E{i:02}" for i in range(40)}:
        parser.error("results.json must contain exactly E00 through E39")

    # The release checksum copy must be recorded before refreshing manifest hashes.
    sums_copy = out_dir / "original-SHA256SUMS.source"
    if not sums_copy.is_file():
        parser.error(f"copy the original release checksum file to {sums_copy} before export")
    original_hashes = {}
    for line in sums_copy.read_text(encoding="utf-8").splitlines():
        m = re.fullmatch(r"([0-9a-f]{64})  (experiments/E[0-9]{2}\.md)", line)
        if m:
            original_hashes[m.group(2).split("/")[-1][:-3]] = m.group(1)
    if set(original_hashes) != {f"E{i:02}" for i in range(40)}:
        parser.error("original checksum copy lacks one or more experiment-card hashes")
    original_body_hashes = {}
    for i in range(40):
        eid = f"E{i:02}"
        try:
            archived = subprocess.run(
                ["git", "show", f"{ARCHIVE_COMMIT}:experiments/{eid}.md"],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ).stdout.decode("utf-8")
            if hashlib.sha256(archived.encode("utf-8")).hexdigest() != original_hashes[eid]:
                parser.error(f"archived card hash disagrees with release checksums: {eid}")
            body = extract_original_protocol_body(archived)
            original_body_hashes[eid] = hashlib.sha256(body.encode("utf-8")).hexdigest()
        except (subprocess.CalledProcessError, UnicodeDecodeError, ValueError) as exc:
            parser.error(f"cannot verify archived protocol body for {eid}: {exc}")

    provenance = {
        "schema_version": 1,
        "campaign_directory": str(run_dir.relative_to(ROOT)) if run_dir.is_relative_to(ROOT) else str(run_dir),
        "campaign_key": config["campaign_key"],
        "run_id": config.get("run_id"),
        "campaign_started_utc": config.get("started_utc"),
        "source_commit": SOURCE_COMMIT,
        "source_commit_url": f"https://github.com/{REPOSITORY}/tree/{SOURCE_COMMIT}",
        "original_protocol_archive_commit": ARCHIVE_COMMIT,
        "original_protocol_archive_url": f"https://github.com/{REPOSITORY}/tree/{ARCHIVE_COMMIT}",
        "original_card_sha256": original_hashes,
        "original_protocol_body_sha256": original_body_hashes,
        "experiment_archive_anchors": {
            eid: {
                "original_card_sha256": original_hashes[eid],
                "original_protocol_body_sha256": original_body_hashes[eid],
            }
            for eid in sorted(original_hashes)
        },
        "original_release_sha256_file_sha256": sha256(sums_copy),
        "campaign_input_sha256": {name: sha256(path) for name, path in inputs.items()},
        "campaign_identity": {
            "source_hashes": config.get("source"),
            "build": {
                "returncode": build.get("build", {}).get("returncode"),
                "binary_sha256": build.get("binary_sha256"),
                "receipt_sha256": sha256(inputs["build.json"]),
            },
            "machine": config.get("machine"),
            "tools": config.get("tools"),
            "identity": config.get("identity"),
            "matrix_sha256": config.get("matrix_sha256"),
            "tools_sha256": config.get("tools_sha256"),
            "final_acceptance_timestamp_utc": acceptance.get("timestamp_utc"),
            "measurement_audit_timestamp_utc": audit.get("snapshot_utc"),
        },
        "cuda_compiled": True,
        "original_release_sha256_file": "original-SHA256SUMS.source",
        "raw_artifacts_in_git": False,
        "raw_campaign_report": "../../../benchmark_runs/v100-20261006T145155Z-4bd01216/REPORT.md",
        "raw_campaign_directory": "../../../benchmark_runs/v100-20261006T145155Z-4bd01216/",
        "analysis_sources": {
            "campaign_report_sha256": sha256(run_dir / "REPORT.md"),
            "independent_measurement_audit_sha256": sha256(run_dir / "offline/measurement-audit.md"),
        },
        "experiment_analysis_provenance": {
            "E23": {
                "source": "../../../benchmark_runs/v100-20261006T145155Z-4bd01216/REPORT.md",
                "measurement_boundary": "Each setup_wall_ms value is one setup observation per case, not repeated timing trials; device_ms contains the repeated timing samples.",
                "claim_scope": "case-level setup observation and device timing only",
            },
            "E33": {
                "source": "../../../benchmark_runs/v100-20261006T145155Z-4bd01216/REPORT.md",
                "primary_timing_selection": "complete native events inside each verified stable interval",
                "full_vector_note": "event_ms and host timestamp vectors span the full resident run; their full-vector medians are distinct from stable-interval primary estimates",
                "claim_scope": "sequential synthetic runs and read-only telemetry estimates; not calibrated wall-plug energy or randomized policy comparison",
            },
            "E39": {
                "source": "../../../benchmark_runs/v100-20261006T145155Z-4bd01216/offline/final-acceptance.json",
                "report_context": "../../../benchmark_runs/v100-20261006T145155Z-4bd01216/REPORT.md",
                "uncertainty_method": acceptance["e39_apparent_crossover_uncertainty"]["method"],
                "difference_ms": acceptance["e39_apparent_crossover_uncertainty"]["difference_ms"],
                "interval_ms": acceptance["e39_apparent_crossover_uncertainty"]["interval_ms"],
                "confidence_level": acceptance["e39_apparent_crossover_uncertainty"]["confidence"],
                "crosses_zero": (acceptance["e39_apparent_crossover_uncertainty"]["interval_ms"][0] <= 0 <=
                                 acceptance["e39_apparent_crossover_uncertainty"]["interval_ms"][1]),
                "established_crossover": acceptance["e39_apparent_crossover_uncertainty"]["established_crossover"],
                "comparison_scope": "bitplane-minus-native complete-path median at size 65536, reuse 8",
                "claim_scope": "within-run sampling uncertainty; not a GPU-kernel-only or between-run claim",
            },
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for i in range(40):
        eid = f"E{i:02}"
        original = copy.deepcopy(results[eid])
        if original.get("experiment") != eid:
            parser.error(f"wrong experiment ID in result record {eid}")
        cases = original.get("samples")
        if not isinstance(cases, list):
            parser.error(f"{eid}: samples must be a list of case records")
        original["samples"] = [compact_case(case) for case in cases]
        (out_dir / f"{eid}.json").write_text(
            json.dumps(original, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps({"exported": 40, "campaign_key": config["campaign_key"],
                      "provenance": str(out_dir / "provenance.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
