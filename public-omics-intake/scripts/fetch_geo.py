#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import (
    append_provenance,
    build_geo_download_plan,
    download_url,
    emit_provenance_event,
    list_ftp_files,
    load_records,
    normalize_accession,
    write_json,
    write_tsv,
)


def planned_geo_files(accession: str, scope: str) -> list[dict[str, Any]]:
    plan = build_geo_download_plan(accession)
    planned: list[dict[str, Any]] = []
    for candidate in plan["download_candidates"]:
        label = candidate["label"]
        if scope == "metadata" and candidate["scope"] != "metadata":
            continue
        if scope == "processed" and candidate["scope"] not in {"metadata", "processed"}:
            continue
        if scope == "all-public" and candidate["scope"] not in {"metadata", "processed"}:
            continue
        if candidate["filename"]:
            planned.append(
                {
                    "accession": accession,
                    "scope": candidate["scope"],
                    "label": label,
                    "url": candidate["url"],
                    "local_path": str(Path(candidate["local_dir"]) / candidate["filename"]),
                }
            )
            continue
        for filename in list_ftp_files(candidate["ftp_dir"]):
            planned.append(
                {
                    "accession": accession,
                    "scope": candidate["scope"],
                    "label": label,
                    "url": f"{candidate['url']}{filename}",
                    "local_path": str(Path(candidate["local_dir"]) / filename),
                }
            )
    return planned


def materialize_geo_files(root: str | Path, files: list[dict[str, Any]], dry_run: bool) -> list[dict[str, Any]]:
    materialized: list[dict[str, Any]] = []
    for entry in files:
        target = Path(root) / entry["local_path"]
        exists = target.exists()
        if not dry_run and not exists:
            download_url(entry["url"], target)
        materialized.append(
            {
                **entry,
                "resolved_path": str(target),
                "downloaded": False if dry_run else not exists,
                "already_present": exists,
            }
        )
    return materialized


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch GEO metadata or processed public files into the canonical source mirror.")
    parser.add_argument("--root", required=True, help="Dataset root.")
    parser.add_argument("--input-json", help="Selected dataset manifest or candidate JSON.")
    parser.add_argument("--accession", action="append", default=[], help="GEO accession. Repeat as needed.")
    parser.add_argument(
        "--scope",
        default="metadata",
        choices=["metadata", "processed", "all-public"],
        help="Requested GEO fetch scope.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Plan without downloading.")
    parser.add_argument("--out-json", required=True, help="File manifest JSON.")
    parser.add_argument("--out-tsv", help="Optional file manifest TSV.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    records: list[dict[str, Any]] = load_records(args.input_json) if args.input_json else []
    accessions = [normalize_accession(item) for item in args.accession]
    accessions.extend(
        normalize_accession(record["primary_accession"])
        for record in records
        if record.get("source") == "geo"
    )
    accessions = sorted(set(accessions))
    planned = []
    for accession in accessions:
        planned.extend(planned_geo_files(accession, args.scope))
    materialized = materialize_geo_files(args.root, planned, args.dry_run)
    payload = {"scope": args.scope, "files": materialized}
    out_json = write_json(args.out_json, payload)
    outputs = [str(out_json)]
    if args.out_tsv:
        out_tsv = write_tsv(args.out_tsv, materialized)
        outputs.append(str(out_tsv))
    event = emit_provenance_event(
        script_name="fetch_geo.py",
        arguments={"scope": args.scope, "dry_run": args.dry_run},
        inputs=[item for item in [args.input_json] if item],
        outputs=outputs,
        endpoint_category="geo",
    )
    append_provenance(args.root, event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
