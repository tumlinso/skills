#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import (
    compute_file_types,
    identifier_consistency,
    list_field,
    linked_accession_completeness,
    load_records,
    metadata_richness,
    read_json,
    unique_sorted,
    write_json,
    write_tsv,
)


def load_weights(path: str | Path) -> dict[str, float]:
    payload = read_json(path)
    return {key: float(value) for key, value in payload.items()}


def normalized_text(record: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "summary", "stage", "tissue", "cell_type", "perturbation", "assay", "chemistry", "modality"):
        value = record.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return " ".join(parts).lower()


def match_any(query_terms: list[str], candidate_values: list[str]) -> float:
    if not query_terms:
        return 1.0
    query = {term.lower() for term in query_terms}
    candidate = {value.lower() for value in candidate_values}
    if query & candidate:
        return 1.0
    if any(any(term in value or value in term for value in candidate) for term in query):
        return 0.7
    return 0.0


def text_match_score(query_terms: list[str], record: dict[str, Any]) -> float:
    if not query_terms:
        return 1.0
    haystack = normalized_text(record)
    hits = sum(1 for term in query_terms if term.lower() in haystack)
    return round(hits / len(query_terms), 4)


def bool_score(value: Any) -> float:
    return 1.0 if bool(value) else 0.0


def score_record(record: dict[str, Any], query_spec: dict[str, Any], weights: dict[str, float]) -> dict[str, Any]:
    species = match_any(query_spec.get("organisms", []), list_field(record.get("species")))
    stage = text_match_score(query_spec.get("developmental_stages", []), record)
    preferred_modalities = query_spec.get("required_modalities") or query_spec.get("preferred_modalities") or []
    modality = match_any(preferred_modalities, list_field(record.get("modality")))
    assay = match_any(preferred_modalities, list_field(record.get("assay")) + list_field(record.get("chemistry")))
    processed = bool_score(record.get("processed_available"))
    raw = bool_score(record.get("raw_available"))
    richness = record.get("metadata_richness")
    if richness in (None, ""):
        richness = metadata_richness(record)
    linked = record.get("linked_accession_completeness")
    if linked in (None, ""):
        linked = linked_accession_completeness(record)
    public_access = 1.0 if record.get("public_access", True) else 0.0
    identifier = record.get("identifier_consistency")
    if identifier in (None, ""):
        identifier = identifier_consistency(record)
    integration = round((processed + richness + linked + identifier + modality + assay) / 6.0, 4)

    factor_scores = {
        "species_match": (species, _species_note(species, query_spec, record)),
        "stage_match": (stage, _stage_note(stage, query_spec, record)),
        "modality_match": (modality, _modality_note(modality, preferred_modalities, record)),
        "assay_compatibility": (assay, _assay_note(assay, preferred_modalities, record)),
        "processed_matrices": (processed, "processed files available" if processed else "processed files not detected"),
        "raw_files": (raw, "raw files available" if raw else "raw files not detected"),
        "metadata_richness": (round(float(richness), 4), "fraction of metadata fields populated"),
        "linked_accessions": (round(float(linked), 4), "study/sample/run linkage completeness"),
        "public_access": (public_access, "publicly accessible" if public_access else "restricted or unclear access"),
        "integration_ease": (integration, "composite estimate from modality, metadata, processed files, and identifier quality"),
        "identifier_consistency": (round(float(identifier), 4), "consistency of linked accessions across layers"),
    }

    breakdown: dict[str, Any] = {}
    total = 0.0
    for factor, (score, rationale) in factor_scores.items():
        weight = float(weights[factor])
        weighted_points = round(score * weight, 4)
        total += weighted_points
        breakdown[factor] = {
            "score": round(score, 4),
            "weight": weight,
            "weighted_points": weighted_points,
            "rationale": rationale,
        }

    ranked = dict(record)
    ranked["file_types_available"] = compute_file_types(record)
    ranked["integratability_score"] = round(total, 4)
    ranked["ranking_breakdown"] = breakdown
    ranked["ranking_rationale"] = summarize_rationale(breakdown)
    return ranked


def summarize_rationale(breakdown: dict[str, Any]) -> list[str]:
    ordered = sorted(
        breakdown.items(),
        key=lambda item: (item[1]["weighted_points"], item[0]),
        reverse=True,
    )
    return [f"{name}: {payload['rationale']}" for name, payload in ordered[:4]]


def rank_records(records: list[dict[str, Any]], query_spec: dict[str, Any], weights: dict[str, float]) -> list[dict[str, Any]]:
    ranked = [score_record(record, query_spec, weights) for record in records]
    ranked.sort(key=lambda record: (-record["integratability_score"], record.get("primary_accession", "")))
    return ranked


def flatten_ranked_record(record: dict[str, Any]) -> dict[str, Any]:
    flattened = {
        "primary_accession": record.get("primary_accession", ""),
        "source": record.get("source", ""),
        "title": record.get("title", ""),
        "species": "|".join(unique_sorted(list_field(record.get("species")))),
        "modality": "|".join(unique_sorted(list_field(record.get("modality")))),
        "assay": "|".join(unique_sorted(list_field(record.get("assay")))),
        "integratability_score": record.get("integratability_score", 0),
        "processed_available": record.get("processed_available", False),
        "raw_available": record.get("raw_available", False),
        "file_types_available": "|".join(unique_sorted(list_field(record.get("file_types_available")))),
        "ranking_rationale": " | ".join(record.get("ranking_rationale", [])),
    }
    for factor, payload in sorted(record.get("ranking_breakdown", {}).items()):
        flattened[f"{factor}_score"] = payload["score"]
        flattened[f"{factor}_weighted_points"] = payload["weighted_points"]
    return flattened


def _species_note(score: float, query_spec: dict[str, Any], record: dict[str, Any]) -> str:
    if not query_spec.get("organisms"):
        return "no organism filter supplied"
    if score == 1.0:
        return "species matches the request"
    return f"requested {query_spec.get('organisms')} but saw {list_field(record.get('species'))}"


def _stage_note(score: float, query_spec: dict[str, Any], record: dict[str, Any]) -> str:
    if not query_spec.get("developmental_stages"):
        return "no stage filter supplied"
    if score > 0:
        return "stage or temporal language overlaps the request"
    return f"stage mismatch against {query_spec.get('developmental_stages')}"


def _modality_note(score: float, modalities: list[str], record: dict[str, Any]) -> str:
    if not modalities:
        return "no modality preference supplied"
    if score == 1.0:
        return "modality directly matches the request"
    if score > 0:
        return "modality partially overlaps the request"
    return f"requested {modalities} but saw {list_field(record.get('modality'))}"


def _assay_note(score: float, modalities: list[str], record: dict[str, Any]) -> str:
    if not modalities:
        return "no assay preference supplied"
    if score == 1.0:
        return "assay or chemistry is compatible with the requested modality"
    if score > 0:
        return "assay or chemistry partially overlaps the request"
    return f"requested {modalities} but saw {list_field(record.get('assay')) + list_field(record.get('chemistry'))}"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank public omics dataset candidates for integratability.")
    parser.add_argument("--input-json", required=True, help="Normalized candidate record JSON.")
    parser.add_argument("--query-spec-json", required=True, help="Structured query specification JSON.")
    parser.add_argument(
        "--weights-json",
        default=str(Path(__file__).with_name("default_ranking_weights.json")),
        help="Ranking weight configuration JSON.",
    )
    parser.add_argument("--out-json", required=True, help="Ranked candidate list JSON.")
    parser.add_argument("--out-tsv", help="Optional ranked candidate TSV.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    weights = load_weights(args.weights_json)
    records = load_records(args.input_json)
    query_spec = read_json(args.query_spec_json)
    ranked = rank_records(records, query_spec, weights)
    payload = {
        "query_spec": query_spec,
        "weights": weights,
        "candidates": ranked,
    }
    write_json(args.out_json, payload)
    if args.out_tsv:
        write_tsv(args.out_tsv, [flatten_ranked_record(record) for record in ranked])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
