#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from common import dump_yaml_like, load_records, slugify, write_tsv


def link_target_for_record(root: str | Path, record: dict[str, Any]) -> Path:
    accession = record["primary_accession"]
    if record.get("source") == "geo":
        return Path(root) / "sources" / "geo" / accession
    return Path(root) / "sources" / "sra" / accession


def ensure_relative_symlink(target: Path, link_path: Path) -> None:
    if link_path.is_symlink():
        if os.readlink(link_path) == os.path.relpath(target, link_path.parent):
            return
        link_path.unlink()
    elif link_path.exists():
        return
    relative_target = os.path.relpath(target, link_path.parent)
    link_path.symlink_to(relative_target)


def build_project_manifest(root: str | Path, project_name: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    project_slug = slugify(project_name)
    return {
        "project_name": project_name,
        "project_slug": project_slug,
        "source_root": str(Path(root) / "sources"),
        "selected_datasets": [
            {
                "primary_accession": record["primary_accession"],
                "source": record["source"],
                "canonical_root": str(link_target_for_record(root, record)),
            }
            for record in records
        ],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create lightweight project links and selection files.")
    parser.add_argument("--root", required=True, help="Dataset root.")
    parser.add_argument("--project-name", required=True, help="Project name.")
    parser.add_argument("--selected-json", required=True, help="Selected dataset manifest JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Plan without creating files.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    records = load_records(args.selected_json)
    project_slug = slugify(args.project_name)
    project_root = Path(args.root) / "projects" / project_slug
    links_dir = project_root / "links"
    if not args.dry_run:
        links_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_project_manifest(args.root, args.project_name, records)
    project_manifest_path = project_root / "project_manifest.yaml"
    selected_tsv_path = project_root / "selected_datasets.tsv"
    notes_path = project_root / "notes.md"
    if not args.dry_run:
        dump_yaml_like(project_manifest_path, manifest)
        write_tsv(
            selected_tsv_path,
            [
                {
                    "primary_accession": record["primary_accession"],
                    "source": record["source"],
                    "title": record.get("title", ""),
                    "integratability_score": record.get("integratability_score", ""),
                }
                for record in records
            ],
        )
        notes_path.write_text(
            "# Project Notes\n\n"
            "This project contains lightweight selection files and links into the canonical source mirror.\n"
        )
        for record in records:
            link_path = links_dir / f"{record['source']}-{record['primary_accession']}"
            ensure_relative_symlink(link_target_for_record(args.root, record), link_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
