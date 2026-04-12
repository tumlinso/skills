#!/usr/bin/env python3
"""Rank normalized paper hits against claims or topic queries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import (
    classify_query_mode,
    dedupe_hits,
    integration_note,
    manuscript_role,
    read_json,
    score_hit,
)


def load_claims(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    if isinstance(payload, dict) and "gaps" in payload:
        claims = []
        for index, gap in enumerate(payload["gaps"], start=1):
            claims.append(
                {
                    "claim_id": gap.get("claim_id") or f"claim-{index}",
                    "query_text": gap.get("sentence", ""),
                    "sentence": gap.get("sentence", ""),
                    "heading": gap.get("heading"),
                    "file": gap.get("file"),
                    "reasons": gap.get("reasons") or [],
                    "suggested_citation_type": gap.get("suggested_citation_type"),
                }
            )
        return claims
    if isinstance(payload, dict) and "claims" in payload:
        return payload["claims"]
    if isinstance(payload, list):
        return payload
    raise ValueError(f"Unsupported claims payload in {path}")


def rank_hits(claims: list[dict[str, Any]], hits: list[dict[str, Any]], *, top_k: int = 5) -> dict[str, Any]:
    hits = dedupe_hits(hits)
    grouped_hits: dict[str, list[dict[str, Any]]] = {}
    for hit in hits:
        grouped_hits.setdefault(hit.get("claim_id") or "", []).append(hit)

    ranked_groups = []
    for claim in claims:
        claim = {**claim}
        claim["query_mode"] = classify_query_mode(claim)
        claim_hits = grouped_hits.get(claim["claim_id"], [])
        scored_hits = []
        for hit in claim_hits:
            score_info = score_hit(claim, hit)
            enriched = {**hit, **score_info}
            enriched["manuscript_role"] = manuscript_role(claim, enriched)
            enriched["integration_note"] = integration_note(claim, enriched)
            scored_hits.append(enriched)
        scored_hits.sort(key=lambda item: item["score"], reverse=True)
        ranked_groups.append(
            {
                "claim_id": claim["claim_id"],
                "query_text": claim.get("query_text"),
                "sentence": claim.get("sentence"),
                "heading": claim.get("heading"),
                "file": claim.get("file"),
                "query_mode": claim["query_mode"],
                "suggested_citation_type": claim.get("suggested_citation_type"),
                "results": scored_hits[:top_k],
                "candidate_count": len(scored_hits),
            }
        )
    return {"claims": claims, "ranked_results": ranked_groups}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hits", required=True, help="Normalized paper hit JSON")
    parser.add_argument("--claims", required=True, help="Claim list or citation-gap JSON")
    parser.add_argument("--top-k", type=int, default=5, help="Top results per claim")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    hits_payload = read_json(Path(args.hits))
    hits = hits_payload["hits"] if isinstance(hits_payload, dict) else hits_payload
    ranked = rank_hits(load_claims(Path(args.claims)), hits, top_k=args.top_k)
    if args.pretty:
        print(json.dumps(ranked, indent=2, sort_keys=True))
    else:
        print(json.dumps(ranked, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
