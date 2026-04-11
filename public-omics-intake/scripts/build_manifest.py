#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import (
    append_provenance,
    compute_file_types,
    emit_provenance_event,
    load_records,
    read_json,
    unique_sorted,
    write_json,
    write_tsv,
)


def select_records(records: list[dict[str, Any]], selected_accessions: list[str] | None) -> list[dict[str, Any]]:
    if not selected_accessions:
        return records
    wanted = {accession.upper() for accession in selected_accessions}
    return [record for record in records if str(record.get("primary_accession", "")).upper() in wanted]


def build_manifest(
    query_spec: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
    selected_accessions: list[str] | None = None,
    fetch_plan: dict[str, Any] | None = None,
    file_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected = []
    for record in select_records(candidates, selected_accessions):
        item = dict(record)
        item["file_types_available"] = compute_file_types(item)
        selected.append(item)
    return {
        "query_spec": query_spec or {},
        "selected_accessions": unique_sorted([record.get("primary_accession", "") for record in selected]),
        "selected_datasets": selected,
        "fetch_plan": fetch_plan or {},
        "file_manifest": file_manifest or {},
        "dataset_count": len(selected),
    }


def flatten_manifest_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "primary_accession": record.get("primary_accession", ""),
        "source": record.get("source", ""),
        "title": record.get("title", ""),
        "species": "|".join(unique_sorted(record.get("species", []))) if isinstance(record.get("species"), list) else record.get("species", ""),
        "modality": "|".join(unique_sorted(record.get("modality", []))) if isinstance(record.get("modality"), list) else record.get("modality", ""),
        "integratability_score": record.get("integratability_score", ""),
        "file_types_available": "|".join(record.get("file_types_available", [])) if isinstance(record.get("file_types_available"), list) else record.get("file_types_available", ""),
        "linked_accessions": "|".join(unique_sorted(record.get("linked_accessions", []))) if isinstance(record.get("linked_accessions"), list) else record.get("linked_accessions", ""),
        "notes": " | ".join(record.get("ranking_rationale", [])) if isinstance(record.get("ranking_rationale"), list) else record.get("notes", ""),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build reproducible selected dataset manifests.")
    parser.add_argument("--candidate-json", required=True, help="Ranked or normalized candidate JSON.")
    parser.add_argument("--query-spec-json", help="Structured query specification JSON.")
    parser.add_argument("--fetch-plan-json", help="Fetch plan JSON.")
    parser.add_argument("--file-manifest-json", help="File manifest JSON.")
    parser.add_argument("--select-accession", action="append", default=[], help="Selected accession. Repeat as needed.")
    parser.add_argument("--out-json", required=True, help="Selected dataset manifest JSON.")
    parser.add_argument("--out-tsv", help="Optional selected dataset TSV.")
    parser.add_argument("--root", help="Dataset root for provenance logging.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    candidate_payload = read_json(args.candidate_json)
    if isinstance(candidate_payload, dict):
        candidates = candidate_payload.get("candidates") or candidate_payload.get("records") or candidate_payload.get("datasets") or []
    else:
        candidates = candidate_payload
    query_spec = read_json(args.query_spec_json) if args.query_spec_json else None
    fetch_plan = read_json(args.fetch_plan_json) if args.fetch_plan_json else None
    file_manifest = read_json(args.file_manifest_json) if args.file_manifest_json else None
    manifest = build_manifest(query_spec, candidates, args.select_accession or None, fetch_plan, file_manifest)
    out_json = write_json(args.out_json, manifest)
    outputs = [str(out_json)]
    if args.out_tsv:
        out_tsv = write_tsv(args.out_tsv, [flatten_manifest_record(record) for record in manifest["selected_datasets"]])
        outputs.append(str(out_tsv))
    if args.root:
        event = emit_provenance_event(
            script_name="build_manifest.py",
            arguments={"selected_accessions": args.select_accession},
            inputs=[item for item in [args.candidate_json, args.query_spec_json, args.fetch_plan_json, args.file_manifest_json] if item],
            outputs=outputs,
        )
        append_provenance(args.root, event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
