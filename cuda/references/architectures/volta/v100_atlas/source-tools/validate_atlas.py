#!/usr/bin/env python3
"""Validate atlas structure, archived protocol anchors and portable evidence."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/evidence/v100-20261006"
SKIP_DIRS = {".git", ".todo-orchestrator", "todos", "build", "benchmark_runs", "__pycache__"}
EXCLUDED_FILES = {
    ROOT / "todos.md",
    ROOT / "todo-status.md",
    ROOT / "experiments/evidence/v100-20261006/VALIDATION.json",
}
ARCHIVE_COMMIT = "5c1f805db80a81f7476ede8292abba69821d104f"
SOURCE_COMMIT = "f223c51dcfacab602e9bc68b3e65cc75730dc7f8"
CAMPAIGN_KEY = "7beacfbd95e0d2b8f9725c7ba1477122f16bc1eb686a6a7c94dbf6c7e266794b"
STATUSES = {"NOT_RUN", "CPU_ONLY", "COMPILED_ONLY", "GPU_RUN", "REJECTED", "INCONCLUSIVE"}


def protocol_body_sha256(text: str) -> str | None:
    """Hash the preserved Question-through-Record body without consulting Git."""
    start = re.search(r"(?m)^\*\*Question:\*\*.*(?:\n|$)", text)
    if start is None:
        return None
    end = re.search(r"(?m)^\*\*Record:\*\*.*(?:\n|$)", text[start.start():])
    if end is None:
        return None
    body = text[start.start():start.start() + end.end()]
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def evidence_matches_status(experiment_id: str, manifest_status: str, summary: dict,
                            provenance: dict, original_card_hash: str,
                            original_body_hash: str) -> bool:
    """Validate status plus shared immutable campaign and protocol anchors."""
    item = provenance.get("experiment_archive_anchors", {}).get(experiment_id, {})
    return (summary.get("experiment") == experiment_id
            and summary.get("status") == manifest_status
            and provenance.get("campaign_key") == CAMPAIGN_KEY
            and provenance.get("source_commit") == SOURCE_COMMIT
            and item.get("original_card_sha256") == original_card_hash
            and item.get("original_protocol_body_sha256") == original_body_hash
            and provenance.get("raw_artifacts_in_git") is False)


def scoped_files(suffix: str):
    """Walk checked-in source and evidence while excluding runtime/build artifacts."""
    for directory, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix == suffix and path not in EXCLUDED_FILES:
                yield path


def main() -> int:
    errors: list[str] = []
    checks = 0

    def check(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    try:
        obj = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    entries = obj["documents"] + obj["sources"]
    known = {d["id"] for d in entries}
    check(len(known) == len(entries), "Duplicate stable IDs")
    expected = ({f"R{i:02}" for i in range(16)} | {f"M{i:02}" for i in range(1, 53)} |
                {f"C{i:02}" for i in range(40)} | {f"E{i:02}" for i in range(40)} |
                {f"S{i:02}" for i in range(1, 43)} | {"A00", "A01", "A02"})
    check(known == expected, "Missing or unexpected document/source IDs")

    provenance_path = EVIDENCE / "provenance.json"
    provenance = {}
    if provenance_path.is_file():
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{provenance_path.relative_to(ROOT)}: {exc}")
    else:
        check(False, "Missing portable campaign provenance")

    original_hashes = provenance.get("original_card_sha256", {})
    original_body_hashes = provenance.get("original_protocol_body_sha256", {})
    check(set(original_hashes) == {f"E{i:02}" for i in range(40)},
          "Provenance lacks original card hashes for E00-E39")
    check(set(original_body_hashes) == {f"E{i:02}" for i in range(40)},
          "Provenance lacks original Question-through-Record body hashes")
    archive_anchors = provenance.get("experiment_archive_anchors", {})
    check(set(archive_anchors) == {f"E{i:02}" for i in range(40)},
          "Per-experiment archive anchors are incomplete")
    analysis_provenance = provenance.get("experiment_analysis_provenance", {})
    check(set(analysis_provenance) == {"E23", "E33", "E39"},
          "Special measurement derivations are missing from shared provenance")
    if "E23" in analysis_provenance:
        check("one setup observation per case" in analysis_provenance["E23"].get("measurement_boundary", ""),
              "E23 setup sample boundary is not explicit")
    if "E39" in analysis_provenance:
        e39 = analysis_provenance["E39"]
        interval = e39.get("interval_ms", [])
        check(e39.get("crosses_zero") is True and len(interval) == 2 and interval[0] <= 0 <= interval[1],
              "E39 bootstrap interval does not transparently cross zero")
    for eid in original_hashes:
        check(archive_anchors.get(eid, {}).get("original_card_sha256") == original_hashes[eid],
              f"Archive card anchor mismatch for {eid}")
        check(archive_anchors.get(eid, {}).get("original_protocol_body_sha256") ==
              original_body_hashes.get(eid), f"Archive protocol-body anchor mismatch for {eid}")
    release_sums = EVIDENCE / "original-SHA256SUMS.source"
    release_card_hashes = {}
    if release_sums.is_file():
        for line in release_sums.read_text(encoding="utf-8").splitlines():
            m = re.fullmatch(r"([0-9a-f]{64})  experiments/(E[0-9]{2})\.md", line)
            if m:
                release_card_hashes[m.group(2)] = m.group(1)
        check(release_card_hashes == original_hashes,
              "Portable original card hashes do not match archived release SHA256SUMS")
        check(hashlib.sha256(release_sums.read_bytes()).hexdigest() ==
              provenance.get("original_release_sha256_file_sha256"),
              "Original release SHA256SUMS copy hash mismatch")
    else:
        check(False, "Missing original release SHA256SUMS copy")
    check(provenance.get("original_protocol_archive_commit") == ARCHIVE_COMMIT,
          "Original protocol archive commit mismatch")
    check(provenance.get("source_commit") == SOURCE_COMMIT,
          "Campaign source commit mismatch")
    check(provenance.get("campaign_key") == CAMPAIGN_KEY,
          "Campaign key does not match the accepted run")
    check(provenance.get("raw_artifacts_in_git") is False,
          "Raw campaign artifacts must remain explicitly outside Git")
    check(bool(provenance.get("campaign_started_utc")), "Campaign timestamp is missing")
    campaign_identity = provenance.get("campaign_identity", {})
    source_hashes = campaign_identity.get("source_hashes", {})
    check(all(re.fullmatch(r"[0-9a-f]{64}", source_hashes.get(k, ""))
              for k in ("files_sha256", "tree_sha256")),
          "Campaign source hashes are incomplete")
    check(isinstance(campaign_identity.get("machine"), dict) and bool(campaign_identity["machine"]),
          "Campaign hardware identity is missing")
    check(isinstance(campaign_identity.get("tools"), dict) and bool(campaign_identity["tools"]),
          "Campaign tool identity is missing")

    summaries: dict[str, dict] = {}
    for d in entries:
        path = (ROOT / d["path"]).resolve()
        check(path.is_relative_to(ROOT), f"Unsafe path {d['path']}")
        check(path.exists(), f"Missing {d['path']}")
        if not path.exists():
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        check(hashlib.sha256(raw).hexdigest() == d.get("sha256"), f"Hash mismatch {d['id']}")
        check(len(text.split()) == d.get("words"), f"Word count mismatch {d['id']}")
        for ref in d.get("requires", []) + d.get("sources", []):
            check(ref in known, f"Unknown dependency {ref} in {d['id']}")
        for ref in set(re.findall(r"(?<![A-Za-z0-9_])(?:R\d{2}|M\d{2}|C\d{2}|E\d{2}|S\d{2})(?![A-Za-z0-9_])", text)):
            check(ref in known, f"Unknown prose reference {ref} in {d['id']}")
        if d.get("kind") != "experiment":
            continue

        eid = d["id"]
        check(d.get("status") in STATUSES, f"Invalid current experiment status {eid}: {d.get('status')}")
        current = re.search(r"\*\*Status:\*\*\s*([A-Z_]+)", text)
        check(bool(current) and current.group(1) == d.get("status"),
              f"Experiment card status does not match manifest for {eid}")
        original_mark = re.search(r"\*\*Original (?:protocol|authoring) status:\*\*\s*([A-Z_]+)", text, re.I)
        check(bool(original_mark) and original_mark.group(1) == "NOT_RUN_ON_GPU",
              f"Missing original NOT_RUN_ON_GPU protocol/authoring status in {eid}")
        check(f"{ARCHIVE_COMMIT}" in text,
              f"Missing immutable original protocol archive reference in {eid}")
        check(f"[Measured summary](evidence/v100-20261006/{eid}.json)" in text,
              f"Missing portable evidence link in {eid}")
        check("[Full campaign](../benchmark_runs/v100-20261006T145155Z-4bd01216/REPORT.md)" in text,
              f"Missing local raw campaign report link in {eid}")
        check(d.get("authoring_status") == "NOT_RUN_ON_GPU",
              f"Manifest did not preserve original authoring status for {eid}")
        actual_body_hash = protocol_body_sha256(text)
        check(actual_body_hash is not None and actual_body_hash == original_body_hashes.get(eid),
              f"Original Question-through-Record protocol body changed in {eid}")

        summary_path = EVIDENCE / f"{eid}.json"
        check(summary_path.is_file(), f"Missing portable evidence summary {eid}")
        if not summary_path.is_file():
            continue
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summaries[eid] = summary
        except Exception as exc:
            errors.append(f"{summary_path.relative_to(ROOT)}: {exc}")
            continue
        check(summary.get("experiment") == eid, f"Wrong evidence ID in {eid}")
        check(summary.get("status") in STATUSES, f"Invalid evidence status in {eid}")
        check(summary.get("status") == d.get("status"), f"Evidence/status mismatch in {eid}")
        check(evidence_matches_status(eid, d.get("status"), summary, provenance,
                                      original_hashes.get(eid), original_body_hashes.get(eid)),
              f"Status or source provenance mismatch in {eid}")
        allowed_result_fields = {"experiment", "status", "hardware", "software", "protocol",
                                 "samples", "correctness", "limitations", "source_hashes",
                                 "date", "result_summary", "raw_artifacts"}
        check(set(summary) == allowed_result_fields,
              f"Portable summary {eid} changes the original result schema fields")
        check(isinstance(summary.get("raw_artifacts"), list), f"Raw artifact locators missing in {eid}")
        # The exported case table retains measured summaries but never the large raw vectors.
        for case in summary.get("samples", []):
            check("configuration" in case and "checks" in case and "metrics" in case and "limitations" in case,
                  f"Incomplete case record in {eid}")
            check(isinstance(case.get("raw_sample_counts"), dict), f"Missing sample counts in {eid}")
            check("samples" not in case, f"Raw sample arrays leaked into portable summary {eid}")
        if summary.get("status") == "GPU_RUN":
            check(summary.get("correctness", {}).get("valid") is True,
                  f"GPU_RUN lacks correctness-passing subset in {eid}")
            check(bool(summary.get("samples")), f"GPU_RUN has no measured cases in {eid}")
        if summary.get("status") in {"NOT_RUN", "REJECTED", "INCONCLUSIVE"}:
            reasons = summary.get("limitations", [])
            check(any(isinstance(r, str) and r.strip() for r in reasons),
                  f"Restricted or unrun status lacks a reason in {eid}")

    index_path = ROOT / "experiments/README.md"
    if index_path.is_file():
        index_text = index_path.read_text(encoding="utf-8")
        for eid, summary in summaries.items():
            row = re.search(rf"(?m)^\| {eid} \| ([A-Z_]+) \|", index_text)
            check(bool(row) and row.group(1) == summary.get("status"),
                  f"Experiment index disposition mismatch for {eid}")
    else:
        check(False, "Missing experiment index README")

    for path in scoped_files(".json"):
        if path == ROOT / "ledger/VALIDATION.json":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            checks += 1
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    for path in scoped_files(".jsonl"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                json.loads(line)
                checks += 1
            except Exception as exc:
                errors.append(f"{path.relative_to(ROOT)} line {line_no}: {exc}")

    # Validate each portable per-ID record with the original schema. The schema
    # package is optional at runtime; absence is reported rather than hidden.
    try:
        import jsonschema  # type: ignore[import-not-found]
        schema = json.loads((ROOT / "experiments/result.schema.json").read_text(encoding="utf-8"))
        for eid in (f"E{i:02}" for i in range(40)):
            path = EVIDENCE / f"{eid}.json"
            if not path.is_file():
                continue
            try:
                jsonschema.validate(json.loads(path.read_text(encoding="utf-8")), schema)
                checks += 1
            except Exception as exc:
                errors.append(f"{path.relative_to(ROOT)} result schema: {exc}")
    except ImportError:
        errors.append("jsonschema is unavailable; original result schema was not verified")

    if obj.get("compendium", {}).get("path"):
        full_path = ROOT / obj["compendium"]["path"]
        check(full_path.is_file(), "Missing compendium")
        if full_path.is_file():
            check(hashlib.sha256(full_path.read_bytes()).hexdigest() == obj["compendium"].get("sha256"),
                  "Compendium hash mismatch")

    build_identity = campaign_identity.get("build", {})
    build_ok = (provenance.get("cuda_compiled") is True
                and build_identity.get("returncode") == 0
                and bool(re.fullmatch(r"[0-9a-f]{64}", build_identity.get("receipt_sha256", ""))))
    # Cross-check raw data when available, but keep validation portable in a clone
    # that intentionally contains no benchmark_runs/ artifacts.
    local_build = ROOT / "benchmark_runs/v100-20261006T145155Z-4bd01216/build.json"
    if local_build.is_file():
        check(hashlib.sha256(local_build.read_bytes()).hexdigest() ==
              provenance.get("campaign_input_sha256", {}).get("build.json"),
              "Local raw build receipt differs from checked-in provenance")
    measured = any(x.get("status") == "GPU_RUN" for x in summaries.values())
    check(obj.get("gpu_measured") is measured, "Manifest GPU measurement flag disagrees with evidence")
    check(obj.get("cuda_compiled") is build_ok, "Manifest CUDA build flag disagrees with build receipt")
    authoring = obj.get("authoring_evidence", {})
    check(authoring.get("gpu_measured") is False and authoring.get("cuda_compiled") is False,
          "Original authoring-time flags were not preserved")
    cpu_path = ROOT / "ledger/CPU_TEST_RESULTS.json"
    try:
        tests = json.loads(cpu_path.read_text(encoding="utf-8"))
        check(tests.get("status") == "PASS", "CPU semantic suite is not PASS")
        check(tests.get("gpu_measured") is False, "CPU test report claims GPU measurement")
        check(tests.get("assertions", 0) > 0, "No CPU assertions recorded")
    except Exception as exc:
        errors.append(f"ledger/CPU_TEST_RESULTS.json: {exc}")

    for path in scoped_files(".md"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
            continue
        check(not re.search(r"POPC\s*14\b", text), f"Known incorrect POPC prior in {path.name}")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
        "validation_scope": "local artifact integrity, portable measured-subset evidence and CPU semantic-record presence; not general performance or domain validation",
        "gpu_measured": measured,
        "cuda_compiled": build_ok,
        "campaign_key": provenance.get("campaign_key"),
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "VALIDATION.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
