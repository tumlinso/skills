#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import (
    append_provenance,
    build_sra_local_root,
    emit_provenance_event,
    load_records,
    normalize_accession,
    run_command,
    write_json,
    write_tsv,
)

from query_sra import resolve_sra_records


def ensure_toolkit() -> None:
    for command in (["prefetch", "--version"],):
        result = run_command(command)
        if result.returncode != 0:
            raise RuntimeError("SRA Toolkit is required for raw SRA acquisition. Could not run prefetch.")


def write_metadata_files(root: str | Path, records: list[dict[str, Any]], runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for record in records:
        accession = normalize_accession(record["primary_accession"])
        local_root = Path(root) / build_sra_local_root(accession)
        metadata_path = local_root / "metadata" / f"{accession}.summary.json"
        runinfo_path = local_root / "runinfo" / f"{accession}.runinfo.tsv"
        write_json(metadata_path, record)
        write_tsv(runinfo_path, [row for row in runs if row["study_accession"] == accession])
        files.append(
            {
                "accession": accession,
                "scope": "metadata",
                "label": "summary-json",
                "resolved_path": str(metadata_path),
            }
        )
        files.append(
            {
                "accession": accession,
                "scope": "metadata",
                "label": "runinfo-tsv",
                "resolved_path": str(runinfo_path),
            }
        )
    return files


def download_raw_runs(root: str | Path, records: list[dict[str, Any]], dry_run: bool, convert_fastq: bool) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    if not records:
        return files
    ensure_toolkit()
    for record in records:
        accession = normalize_accession(record["primary_accession"])
        local_root = Path(root) / build_sra_local_root(accession)
        sra_dir = local_root / "sra"
        fastq_dir = local_root / "fastq"
        tmp_dir = Path(root) / "tmp" / accession
        sra_dir.mkdir(parents=True, exist_ok=True)
        if convert_fastq:
            fastq_dir.mkdir(parents=True, exist_ok=True)
            tmp_dir.mkdir(parents=True, exist_ok=True)
        for run_accession in record.get("run_accessions", []):
            planned_sra = sra_dir / run_accession / f"{run_accession}.sra"
            if not dry_run:
                result = run_command(["prefetch", run_accession, "-O", str(sra_dir)])
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or f"prefetch failed for {run_accession}")
                if convert_fastq:
                    result = run_command(
                        [
                            "fasterq-dump",
                            run_accession,
                            "--outdir",
                            str(fastq_dir),
                            "--temp",
                            str(tmp_dir),
                        ]
                    )
                    if result.returncode != 0:
                        raise RuntimeError(result.stderr.strip() or f"fasterq-dump failed for {run_accession}")
            files.append(
                {
                    "accession": accession,
                    "run_accession": run_accession,
                    "scope": "raw",
                    "label": "sra",
                    "resolved_path": str(planned_sra),
                    "downloaded": not dry_run,
                }
            )
    return files


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch SRA metadata or raw runs into the canonical source mirror.")
    parser.add_argument("--root", required=True, help="Dataset root.")
    parser.add_argument("--input-json", help="Selected dataset manifest or candidate JSON.")
    parser.add_argument("--description", help="Freeform biological description when querying directly.")
    parser.add_argument("--accession", action="append", default=[], help="SRA/BioProject accession. Repeat as needed.")
    parser.add_argument(
        "--scope",
        default="metadata",
        choices=["metadata", "raw", "all-public"],
        help="Requested SRA fetch scope.",
    )
    parser.add_argument("--convert-fastq", action="store_true", help="Also materialize FASTQ files after prefetch.")
    parser.add_argument("--dry-run", action="store_true", help="Plan without downloading.")
    parser.add_argument("--out-json", required=True, help="File manifest JSON.")
    parser.add_argument("--out-tsv", help="Optional file manifest TSV.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.input_json:
        payload = load_records(args.input_json)
        records = [record for record in payload if record.get("source") == "sra"]
        runs: list[dict[str, Any]] = []
    else:
        _, records, runs = resolve_sra_records(args.description, args.accession, retmax=20)
    manifest_files = write_metadata_files(args.root, records, runs) if args.scope in {"metadata", "all-public", "raw"} else []
    if args.scope in {"raw", "all-public"}:
        manifest_files.extend(download_raw_runs(args.root, records, args.dry_run, args.convert_fastq))
    payload = {"scope": args.scope, "files": manifest_files}
    out_json = write_json(args.out_json, payload)
    outputs = [str(out_json)]
    if args.out_tsv:
        out_tsv = write_tsv(args.out_tsv, manifest_files)
        outputs.append(str(out_tsv))
    event = emit_provenance_event(
        script_name="fetch_sra.py",
        arguments={
            "scope": args.scope,
            "dry_run": args.dry_run,
            "convert_fastq": args.convert_fastq,
        },
        inputs=[item for item in [args.input_json] if item],
        outputs=outputs,
        endpoint_category="sra",
    )
    append_provenance(args.root, event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
