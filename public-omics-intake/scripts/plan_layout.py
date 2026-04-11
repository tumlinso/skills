#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import (
    append_provenance,
    build_sra_local_root,
    build_geo_download_plan,
    emit_provenance_event,
    load_records,
    normalize_accession,
    slugify,
    write_json,
)


ROOT_DIRS = [
    "registry/searches",
    "registry/manifests",
    "registry/plans",
    "registry/provenance",
    "sources/geo",
    "sources/sra",
    "projects",
    "tmp",
]


def build_layout_plan(
    root: str | Path,
    project_name: str,
    records: list[dict[str, Any]],
    fetch_scope: str,
) -> dict[str, Any]:
    root = Path(root)
    project_slug = slugify(project_name)
    datasets: list[dict[str, Any]] = []
    for record in records:
        accession = normalize_accession(record.get("primary_accession") or record.get("accession"))
        source = record.get("source")
        if source == "geo":
            geo_plan = build_geo_download_plan(accession)
            datasets.append(
                {
                    "source": "geo",
                    "primary_accession": accession,
                    "canonical_root": str(root / geo_plan["local_root"]),
                    "metadata_dir": str(root / geo_plan["metadata_dir"]),
                    "soft_dir": str(root / geo_plan["soft_dir"]),
                    "miniml_dir": str(root / geo_plan["miniml_dir"]),
                    "matrix_dir": str(root / geo_plan["matrix_dir"]),
                    "suppl_dir": str(root / geo_plan["suppl_dir"]),
                    "fetch_scope": fetch_scope,
                }
            )
        elif source == "sra":
            local_root = build_sra_local_root(accession)
            datasets.append(
                {
                    "source": "sra",
                    "primary_accession": accession,
                    "canonical_root": str(root / local_root),
                    "metadata_dir": str(root / local_root / Path("metadata")),
                    "runinfo_dir": str(root / local_root / Path("runinfo")),
                    "sra_dir": str(root / local_root / Path("sra")),
                    "fastq_dir": str(root / local_root / Path("fastq")),
                    "fetch_scope": fetch_scope,
                }
            )
        else:
            raise ValueError(f"Unsupported source for layout planning: {source}")

    project_root = root / "projects" / project_slug
    return {
        "root": str(root),
        "project_name": project_name,
        "project_slug": project_slug,
        "fetch_scope": fetch_scope,
        "dry_run_supported": True,
        "root_directories": [str(root / directory) for directory in ROOT_DIRS],
        "project_paths": {
            "project_root": str(project_root),
            "project_manifest_yaml": str(project_root / "project_manifest.yaml"),
            "selected_datasets_tsv": str(project_root / "selected_datasets.tsv"),
            "notes_md": str(project_root / "notes.md"),
            "links_dir": str(project_root / "links"),
        },
        "registry_paths": {
            "searches_dir": str(root / "registry" / "searches"),
            "manifests_dir": str(root / "registry" / "manifests"),
            "plans_dir": str(root / "registry" / "plans"),
            "provenance_dir": str(root / "registry" / "provenance"),
        },
        "datasets": datasets,
    }


def materialize_layout(plan: dict[str, Any]) -> None:
    for directory in plan["root_directories"]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    project_paths = plan["project_paths"]
    Path(project_paths["project_root"]).mkdir(parents=True, exist_ok=True)
    Path(project_paths["links_dir"]).mkdir(parents=True, exist_ok=True)
    for dataset in plan["datasets"]:
        for key, value in dataset.items():
            if key.endswith("_dir") or key == "canonical_root":
                Path(value).mkdir(parents=True, exist_ok=True)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan the canonical on-disk layout for public omics intake.")
    parser.add_argument("--root", required=True, help="Dataset root.")
    parser.add_argument("--project-name", required=True, help="Project name used under projects/.")
    parser.add_argument("--selected-json", required=True, help="Selected dataset manifest JSON or candidate list JSON.")
    parser.add_argument(
        "--fetch-scope",
        default="metadata",
        choices=["metadata", "processed", "raw", "all-public"],
        help="Requested fetch scope.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Plan only. Do not create directories.")
    parser.add_argument("--out-json", required=True, help="Layout plan JSON output.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    records = load_records(args.selected_json)
    plan = build_layout_plan(args.root, args.project_name, records, args.fetch_scope)
    if not args.dry_run:
        materialize_layout(plan)
    out_path = write_json(args.out_json, plan)
    provenance = emit_provenance_event(
        script_name="plan_layout.py",
        arguments={
            "root": args.root,
            "project_name": args.project_name,
            "fetch_scope": args.fetch_scope,
            "dry_run": args.dry_run,
        },
        inputs=[args.selected_json],
        outputs=[str(out_path)],
    )
    append_provenance(args.root, provenance)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
