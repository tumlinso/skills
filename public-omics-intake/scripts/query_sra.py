#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
from collections import defaultdict
from typing import Any
from urllib.parse import urlencode

from common import (
    NCBI_EUTILS_BASE,
    compute_file_types,
    linked_accession_completeness,
    metadata_richness,
    normalize_accession,
    parse_request_description,
    request_json,
    request_text,
    unique_sorted,
    write_json,
    write_tsv,
)


def build_sra_search_term(query_spec: dict[str, Any]) -> str:
    pieces = [query_spec.get("description", "").strip()]
    pieces.extend(query_spec.get("organisms", []))
    pieces.extend(query_spec.get("preferred_modalities", []))
    pieces.extend(query_spec.get("developmental_stages", []))
    pieces.extend(query_spec.get("tissues", []))
    return " ".join(piece for piece in pieces if piece)


def esearch_sra_ids(term: str, retmax: int) -> list[str]:
    payload = request_json(
        "esearch.fcgi",
        {"db": "sra", "term": term, "retmode": "json", "retmax": retmax},
    )
    return payload.get("esearchresult", {}).get("idlist", [])


def accession_search_ids(accessions: list[str]) -> list[str]:
    ids: list[str] = []
    for accession in accessions:
        payload = request_json(
            "esearch.fcgi",
            {"db": "sra", "term": accession, "retmode": "json", "retmax": 20},
        )
        ids.extend(payload.get("esearchresult", {}).get("idlist", []))
    return unique_sorted(ids)


def fetch_runinfo_rows(ids: list[str]) -> list[dict[str, str]]:
    if not ids:
        return []
    query = urlencode({"db": "sra", "id": ",".join(ids), "rettype": "runinfo", "retmode": "text"})
    text = request_text(f"{NCBI_EUTILS_BASE}/efetch.fcgi?{query}")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def modality_from_runinfo(row: dict[str, str]) -> list[str]:
    strategy = (row.get("LibraryStrategy") or "").lower()
    layout = (row.get("LibraryLayout") or "").lower()
    modalities: list[str] = []
    if "rna-seq" in strategy and "single" in (row.get("LibraryName") or "").lower():
        modalities.append("scrna-seq")
    elif "rna-seq" in strategy:
        modalities.append("bulk-rna-seq")
    if "atac" in strategy:
        modalities.append("scatac-seq")
    if "cite" in strategy:
        modalities.append("cite-seq")
    if "paired" in layout and "atac" in strategy and "rna" in strategy:
        modalities.append("multiome")
    return modalities or [strategy or "unknown"]


def normalize_sra_records(run_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    studies: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in run_rows:
        study_accession = row.get("BioProject") or row.get("SRAStudy") or row.get("Study")
        if not study_accession:
            continue
        studies[study_accession].append(row)

    normalized_studies: list[dict[str, Any]] = []
    normalized_runs: list[dict[str, Any]] = []
    for study_accession, rows in studies.items():
        normalized_runs.extend(
            {
                "study_accession": study_accession,
                "run_accession": row.get("Run", ""),
                "experiment_accession": row.get("Experiment", ""),
                "sample_accession": row.get("BioSample") or row.get("Sample", ""),
                "species": row.get("ScientificName", ""),
                "library_strategy": row.get("LibraryStrategy", ""),
                "library_layout": row.get("LibraryLayout", ""),
                "platform": row.get("Platform", ""),
                "model": row.get("Model", ""),
                "pubmed_id": row.get("Study_Pubmed_id", ""),
                "download_path": row.get("download_path", ""),
            }
            for row in rows
        )
        modalities = unique_sorted(modality for row in rows for modality in modality_from_runinfo(row))
        record = {
            "source": "sra",
            "primary_accession": normalize_accession(study_accession),
            "study_accessions": [normalize_accession(study_accession)],
            "sample_accessions": unique_sorted(row.get("BioSample") or row.get("Sample", "") for row in rows),
            "run_accessions": unique_sorted(row.get("Run", "") for row in rows),
            "title": rows[0].get("LibraryName") or rows[0].get("Study", study_accession),
            "summary": "",
            "species": unique_sorted(row.get("ScientificName", "") for row in rows),
            "modality": modalities,
            "assay": unique_sorted(row.get("LibraryStrategy", "") for row in rows),
            "chemistry": unique_sorted(row.get("Platform", "") for row in rows),
            "stage": "",
            "tissue": unique_sorted(row.get("Body_Site", "") for row in rows if row.get("Body_Site")),
            "cell_type": "",
            "perturbation": "",
            "processed_available": False,
            "raw_available": bool(rows),
            "metadata_richness": 0.0,
            "linked_accession_completeness": 0.0,
            "public_access": True,
            "identifier_consistency": 0.0,
            "pubmed_ids": unique_sorted(row.get("Study_Pubmed_id", "") for row in rows),
            "available_file_types": ["runinfo", "raw"],
            "download_candidates": [
                {
                    "scope": "metadata",
                    "label": "runinfo",
                    "filename": f"{normalize_accession(study_accession)}.runinfo.tsv",
                    "local_dir": f"sources/sra/{normalize_accession(study_accession)}/runinfo",
                },
                {
                    "scope": "raw",
                    "label": "sra",
                    "filename": None,
                    "local_dir": f"sources/sra/{normalize_accession(study_accession)}/sra",
                    "run_accessions": unique_sorted(row.get("Run", "") for row in rows),
                },
            ],
            "linked_accessions": unique_sorted(
                [
                    normalize_accession(study_accession),
                    *[row.get("BioSample") or row.get("Sample", "") for row in rows],
                    *[row.get("Run", "") for row in rows],
                ]
            ),
        }
        record["metadata_richness"] = metadata_richness(record)
        record["linked_accession_completeness"] = linked_accession_completeness(record)
        record["identifier_consistency"] = record["linked_accession_completeness"]
        record["file_types_available"] = compute_file_types(record)
        normalized_studies.append(record)
    normalized_studies.sort(key=lambda item: item["primary_accession"])
    normalized_runs.sort(key=lambda item: (item["study_accession"], item["run_accession"]))
    return normalized_studies, normalized_runs


def resolve_sra_records(
    description: str | None,
    accessions: list[str],
    retmax: int,
    organisms: list[str] | None = None,
    preferred_modalities: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    query_spec = parse_request_description(
        description or " ".join(accessions),
        organisms=organisms,
        preferred_modalities=preferred_modalities,
    )
    ids = accession_search_ids(accessions) if accessions else []
    if description:
        ids.extend(esearch_sra_ids(build_sra_search_term(query_spec), retmax))
    ids = unique_sorted(ids)[:retmax]
    run_rows = fetch_runinfo_rows(ids)
    records, runs = normalize_sra_records(run_rows)
    return query_spec, records, runs


def flatten_sra_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "primary_accession": record["primary_accession"],
        "source": record["source"],
        "title": record["title"],
        "species": "|".join(record.get("species", [])),
        "modality": "|".join(record.get("modality", [])),
        "assay": "|".join(record.get("assay", [])),
        "run_count": len(record.get("run_accessions", [])),
        "sample_count": len(record.get("sample_accessions", [])),
        "raw_available": record.get("raw_available", False),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query SRA metadata and emit normalized study and run records.")
    parser.add_argument("--description", help="Freeform biological description.")
    parser.add_argument("--accession", action="append", default=[], help="SRA/BioProject accession. Repeat as needed.")
    parser.add_argument("--organism", action="append", default=[], help="Preferred organism. Repeat as needed.")
    parser.add_argument("--preferred-modality", action="append", default=[], help="Preferred modality. Repeat as needed.")
    parser.add_argument("--retmax", type=int, default=20, help="Maximum SRA ids to resolve.")
    parser.add_argument("--out-json", required=True, help="Output JSON path.")
    parser.add_argument("--out-tsv", help="Optional TSV output path.")
    parser.add_argument("--out-run-tsv", help="Optional run metadata TSV output path.")
    parser.add_argument("--query-spec-json", help="Optional query spec JSON output path.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    query_spec, records, run_rows = resolve_sra_records(
        description=args.description,
        accessions=[normalize_accession(accession) for accession in args.accession],
        retmax=args.retmax,
        organisms=args.organism,
        preferred_modalities=args.preferred_modality,
    )
    payload = {"query_spec": query_spec, "records": records, "runs": run_rows}
    write_json(args.out_json, payload)
    if args.out_tsv:
        write_tsv(args.out_tsv, [flatten_sra_record(record) for record in records])
    if args.out_run_tsv:
        write_tsv(args.out_run_tsv, run_rows)
    if args.query_spec_json:
        write_json(args.query_spec_json, query_spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
