#!/usr/bin/env python3
"""Search bioRxiv by scanning recent metadata and ranking abstracts locally."""

from __future__ import annotations

import argparse
import json
from typing import Any

from common import (
    fetch_json,
    infer_paper_kind,
    maybe_int,
    normalize_whitespace,
    recent_date_range,
    score_hit,
)

BIORXIV_URL = "https://api.biorxiv.org/details/biorxiv"


def parse_biorxiv_payload(payload: dict[str, Any], query_text: str, claim_id: str | None = None) -> list[dict[str, Any]]:
    collection = payload.get("collection", [])
    hits: list[dict[str, Any]] = []
    for item in collection:
        doi = normalize_whitespace(item.get("doi", ""))
        hit = {
            "source": "biorxiv",
            "source_id": doi or normalize_whitespace(item.get("title", "")),
            "title": normalize_whitespace(item.get("title", "")),
            "authors": [normalize_whitespace(part) for part in (item.get("authors", "") or "").split(";") if normalize_whitespace(part)],
            "year": (item.get("date") or "")[:4],
            "date": item.get("date", ""),
            "venue": "bioRxiv",
            "abstract": normalize_whitespace(item.get("abstract", "")),
            "url": f"https://www.biorxiv.org/content/{doi}v{item.get('version', '1')}" if doi else "",
            "doi": doi,
            "categories": [normalize_whitespace(item.get("category", ""))] if item.get("category") else [],
            "publication_types": [],
            "paper_kind": "",
            "query_text": query_text,
            "claim_id": claim_id,
        }
        hit["paper_kind"] = infer_paper_kind(hit)
        hits.append(hit)
    return hits


def fetch_biorxiv_window(*, lookback_days: int, scan_limit: int) -> list[dict[str, Any]]:
    start_date, end_date = recent_date_range(lookback_days)
    cursor = 0
    collected: list[dict[str, Any]] = []
    while len(collected) < scan_limit:
        payload = fetch_json(f"{BIORXIV_URL}/{start_date}/{end_date}/{cursor}/json")
        batch = payload.get("collection", [])
        if not batch:
            break
        collected.extend(batch)
        messages = payload.get("messages", [])
        total = maybe_int(messages[0].get("total")) if messages else None
        cursor += len(batch)
        if total is not None and cursor >= total:
            break
        if len(batch) < 100:
            break
    return collected[:scan_limit]


def search_biorxiv(
    query_text: str,
    *,
    top_k: int = 8,
    claim_id: str | None = None,
    lookback_days: int = 365,
    scan_limit: int = 300,
) -> list[dict[str, Any]]:
    payload = {"collection": fetch_biorxiv_window(lookback_days=lookback_days, scan_limit=scan_limit)}
    hits = parse_biorxiv_payload(payload, query_text, claim_id=claim_id)
    claim = {"claim_id": claim_id, "query_text": query_text, "sentence": query_text}
    ranked = []
    for hit in hits:
        score_info = score_hit(claim, hit)
        hit = {**hit, **score_info}
        ranked.append(hit)
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_k]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="bioRxiv query text")
    parser.add_argument("--top-k", type=int, default=8, help="Maximum papers to return after ranking")
    parser.add_argument("--claim-id", default=None, help="Optional claim identifier")
    parser.add_argument("--lookback-days", type=int, default=365, help="How many recent days of bioRxiv metadata to scan")
    parser.add_argument("--scan-limit", type=int, default=300, help="Maximum number of bioRxiv records to scan before ranking")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    hits = search_biorxiv(
        args.query,
        top_k=args.top_k,
        claim_id=args.claim_id,
        lookback_days=args.lookback_days,
        scan_limit=args.scan_limit,
    )
    payload = {
        "source": "biorxiv",
        "query": args.query,
        "claim_id": args.claim_id,
        "lookback_days": args.lookback_days,
        "hits": hits,
    }
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
