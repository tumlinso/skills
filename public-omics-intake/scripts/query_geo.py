#!/usr/bin/env python3
from __future__ import annotations

import argparse
from typing import Any

from common import (
    build_geo_download_plan,
    compute_file_types,
    linked_accession_completeness,
    metadata_richness,
    normalize_accession,
    parse_request_description,
    request_json,
    unique_sorted,
    write_json,
    write_tsv,
)


def build_geo_search_term(query_spec: dict[str, Any]) -> str:
    terms = [query_spec.get("description", "").strip()]
    for organism in query_spec.get("organisms", []):
        terms.append(organism)
    for modality in query_spec.get("preferred_modalities", []):
        terms.append(modality)
    for stage in query_spec.get("developmental_stages", []):
        terms.append(stage)
    for tissue in query_spec.get("tissues", []):
        terms.append(tissue)
    return " ".join(term for term in terms if term)


def esearch_geo_ids(term: str, retmax: int) -> list[str]:
    payload = request_json(
        "esearch.fcgi",
        {"db": "gds", "term": term, "retmode": "json", "retmax": retmax},
    )
    return payload.get("esearchresult", {}).get("idlist", [])


def esummary_geo(ids: list[str]) -> dict[str, Any]:
    if not ids:
        return {"result": {"uids": []}}
    return request_json(
        "esummary.fcgi",
        {"db": "gds", "id": ",".join(ids), "retmode": "json"},
    )


def accession_search_ids(accessions: list[str]) -> list[str]:
    found: list[str] = []
    for accession in accessions:
        payload = request_json(
            "esearch.fcgi",
            {"db": "gds", "term": f"{accession}[ACCN]", "retmode": "json", "retmax": 5},
        )
        found.extend(payload.get("esearchresult", {}).get("idlist", []))
    return unique_sorted(found)


def normalize_geo_record(doc: dict[str, Any]) -> dict[str, Any]:
    accession = normalize_accession(doc.get("accession", ""))
    description_blob = " ".join(str(doc.get(key, "")) for key in ("summary", "title", "taxon", "gdstype"))
    modality = infer_geo_modality(description_blob)
    plan = build_geo_download_plan(accession)
    species = doc.get("taxon", [])
    if isinstance(species, str):
        species = [species]
    record = {
        "source": "geo",
        "primary_accession": accession,
        "study_accessions": [accession] if accession.startswith("GSE") else [],
        "sample_accessions": [],
        "run_accessions": [],
        "title": doc.get("title", ""),
        "summary": doc.get("summary", ""),
        "species": species,
        "modality": modality,
        "assay": [doc.get("gdstype", "")] if doc.get("gdstype") else [],
        "chemistry": [],
        "stage": doc.get("subsetinfo", ""),
        "tissue": "",
        "cell_type": "",
        "perturbation": "",
        "processed_available": accession.startswith("GSE"),
        "raw_available": False,
        "metadata_richness": 0.0,
        "linked_accession_completeness": 0.0,
        "public_access": True,
        "identifier_consistency": 1.0 if accession.startswith("GSE") else 0.75,
        "pubmed_ids": [str(doc["pubmedids"])] if doc.get("pubmedids") else [],
        "available_file_types": ["soft", "miniml", "processed"] if accession.startswith("GSE") else ["processed"],
        "download_candidates": plan["download_candidates"],
        "notes": [f"entry_type={doc.get('entrytype', '')}".strip("=")],
        "linked_accessions": [accession],
    }
    record["metadata_richness"] = metadata_richness(record)
    record["linked_accession_completeness"] = linked_accession_completeness(record)
    record["file_types_available"] = compute_file_types(record)
    return record


def infer_geo_modality(text: str) -> list[str]:
    lowered = text.lower()
    modalities: list[str] = []
    if "single cell" in lowered or "single-cell" in lowered or "scrna" in lowered:
        modalities.append("scrna-seq")
    if "spatial" in lowered:
        modalities.append("spatial-transcriptomics")
    if "atac" in lowered:
        modalities.append("scatac-seq")
    if not modalities and ("rna" in lowered or "transcript" in lowered):
        modalities.append("bulk-rna-seq")
    return modalities


def flatten_geo_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "primary_accession": record["primary_accession"],
        "source": record["source"],
        "title": record["title"],
        "species": "|".join(record.get("species", [])),
        "modality": "|".join(record.get("modality", [])),
        "assay": "|".join(record.get("assay", [])),
        "processed_available": record.get("processed_available", False),
        "raw_available": record.get("raw_available", False),
        "file_types_available": "|".join(record.get("file_types_available", [])),
    }


def resolve_geo_records(
    description: str | None,
    accessions: list[str],
    retmax: int,
    organisms: list[str] | None = None,
    preferred_modalities: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    query_spec = parse_request_description(
        description or " ".join(accessions),
        organisms=organisms,
        preferred_modalities=preferred_modalities,
    )
    ids = accession_search_ids(accessions) if accessions else []
    if description:
        ids.extend(esearch_geo_ids(build_geo_search_term(query_spec), retmax))
    ids = unique_sorted(ids)[:retmax]
    summary = esummary_geo(ids)
    docs = []
    for uid in summary.get("result", {}).get("uids", []):
        doc = summary["result"].get(uid)
        if isinstance(doc, dict) and doc.get("accession"):
            docs.append(normalize_geo_record(doc))
    return query_spec, docs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query GEO metadata and emit normalized records.")
    parser.add_argument("--description", help="Freeform biological description.")
    parser.add_argument("--accession", action="append", default=[], help="GEO accession. Repeat as needed.")
    parser.add_argument("--organism", action="append", default=[], help="Preferred organism. Repeat as needed.")
    parser.add_argument("--preferred-modality", action="append", default=[], help="Preferred modality. Repeat as needed.")
    parser.add_argument("--retmax", type=int, default=20, help="Maximum GEO records to return.")
    parser.add_argument("--out-json", required=True, help="Output JSON path.")
    parser.add_argument("--out-tsv", help="Optional TSV output path.")
    parser.add_argument("--query-spec-json", help="Optional query spec JSON output path.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    query_spec, records = resolve_geo_records(
        description=args.description,
        accessions=[normalize_accession(accession) for accession in args.accession],
        retmax=args.retmax,
        organisms=args.organism,
        preferred_modalities=args.preferred_modality,
    )
    payload = {"query_spec": query_spec, "records": records}
    write_json(args.out_json, payload)
    if args.out_tsv:
        write_tsv(args.out_tsv, [flatten_geo_record(record) for record in records])
    if args.query_spec_json:
        write_json(args.query_spec_json, query_spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
