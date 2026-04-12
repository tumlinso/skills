#!/usr/bin/env python3
"""Build a compact abstract-first citation shortlist."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import (
    dedupe_hits,
    ensure_dir,
    read_json,
    safe_slug,
    write_json,
    write_text,
)
from export_bibtex import export_bibtex
from rank_paper_hits import rank_hits
from search_arxiv import search_arxiv
from search_biorxiv import search_biorxiv
from search_pubmed import search_pubmed

SOURCE_FUNCS = {
    "pubmed": search_pubmed,
    "biorxiv": search_biorxiv,
    "arxiv": search_arxiv,
}


def _quarto_extract_script() -> Path:
    return Path(__file__).resolve().parent / "extract_citation_gaps.py"


def claims_from_gap_payload(payload: dict[str, Any], *, max_claims: int) -> list[dict[str, Any]]:
    claims = []
    for index, gap in enumerate(payload.get("gaps", [])[:max_claims], start=1):
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


def claims_from_input(input_path: Path, *, max_claims: int) -> list[dict[str, Any]]:
    if input_path.suffix.lower() == ".json":
        payload = read_json(input_path)
        if isinstance(payload, dict) and "gaps" in payload:
            return claims_from_gap_payload(payload, max_claims=max_claims)
        if isinstance(payload, dict) and "claims" in payload:
            return payload["claims"][:max_claims]
        raise ValueError(f"Unsupported JSON input for citation scouting: {input_path}")

    script = _quarto_extract_script()
    if not script.exists():
        raise FileNotFoundError(f"Could not find quarto-manuscript extractor at {script}")
    result = subprocess.run(
        [sys.executable, str(script), str(input_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return claims_from_gap_payload(json.loads(result.stdout), max_claims=max_claims)


def run_searches(
    claims: list[dict[str, Any]],
    *,
    sources: list[str],
    top_k: int,
    lookback_days: int,
    scan_limit: int,
    email: str | None,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for claim in claims:
        for source in sources:
            if source == "pubmed":
                source_hits = SOURCE_FUNCS[source](claim["query_text"], top_k=top_k * 2, claim_id=claim["claim_id"], email=email)
            elif source == "biorxiv":
                source_hits = SOURCE_FUNCS[source](
                    claim["query_text"],
                    top_k=top_k * 2,
                    claim_id=claim["claim_id"],
                    lookback_days=lookback_days,
                    scan_limit=scan_limit,
                )
            else:
                source_hits = SOURCE_FUNCS[source](claim["query_text"], top_k=top_k * 2, claim_id=claim["claim_id"])
            hits.extend(source_hits)
    return dedupe_hits(hits)


def build_shortlist_text(shortlist: list[dict[str, Any]], *, sources: list[str], input_mode: str) -> str:
    lines = [
        f"Input mode: {input_mode}",
        f"Sources searched: {', '.join(sources)}",
        "",
    ]
    for index, group in enumerate(shortlist, start=1):
        lines.append(f"{index}. {group.get('sentence') or group.get('query_text')}")
        lines.append(f"   Query mode: {group.get('query_mode')} | candidates: {group.get('candidate_count')}")
        if not group.get("results"):
            lines.append("   No strong abstract-level matches found.")
            lines.append("")
            continue
        for hit in group["results"]:
            lines.append(
                "   - "
                + f"{hit.get('title')} [{hit.get('source')}, {hit.get('paper_kind')}, score={hit.get('score')}]"
            )
            lines.append(f"     Why: {hit.get('integration_note')}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=None, help="Citation-gap JSON, manuscript path, or manuscript directory")
    parser.add_argument("--query", default=None, help="Direct topic query")
    parser.add_argument("--sources", default="pubmed,biorxiv,arxiv", help="Comma-separated source list")
    parser.add_argument("--top-k", type=int, default=5, help="Top results per claim in the final shortlist")
    parser.add_argument("--output-dir", required=True, help="Directory for output artifacts")
    parser.add_argument("--max-claims", type=int, default=5, help="Maximum manuscript claims to expand in one run")
    parser.add_argument("--lookback-days", type=int, default=365, help="bioRxiv recent-window scan size in days")
    parser.add_argument("--scan-limit", type=int, default=300, help="Maximum bioRxiv records to scan before ranking")
    parser.add_argument("--emit-bibtex", action="store_true", help="Emit shortlist.bib")
    parser.add_argument("--email", default=None, help="Optional email for NCBI etiquette")
    parser.add_argument("--abstract-only", action="store_true", help="Accepted for compatibility; v1 is abstract-only")
    args = parser.parse_args()

    if not args.input and not args.query:
        raise SystemExit("Provide either --input or --query.")

    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)
    sources = [item.strip() for item in args.sources.split(",") if item.strip()]

    if args.query:
        claims = [
            {
                "claim_id": f"query-{safe_slug(args.query)[:32]}",
                "query_text": args.query,
                "sentence": args.query,
                "heading": None,
                "file": None,
                "reasons": [],
                "suggested_citation_type": None,
            }
        ]
        input_mode = "topic-query"
    else:
        claims = claims_from_input(Path(args.input), max_claims=args.max_claims)
        input_mode = "manuscript-linked"

    hits = run_searches(
        claims,
        sources=sources,
        top_k=args.top_k,
        lookback_days=args.lookback_days,
        scan_limit=args.scan_limit,
        email=args.email,
    )
    ranked = rank_hits(claims, hits, top_k=args.top_k)
    shortlist_json = {
        "input_mode": input_mode,
        "sources": sources,
        "shortlist": ranked["ranked_results"],
    }

    paper_hits_path = output_dir / "paper_hits.json"
    shortlist_json_path = output_dir / "shortlist.json"
    shortlist_txt_path = output_dir / "shortlist.txt"

    write_json(paper_hits_path, {"claims": claims, "hits": hits})
    write_json(shortlist_json_path, shortlist_json)
    write_text(shortlist_txt_path, build_shortlist_text(ranked["ranked_results"], sources=sources, input_mode=input_mode))

    bibtex_path = None
    if args.emit_bibtex:
        bibtex_path = output_dir / "shortlist.bib"
        unique_hits = []
        seen = set()
        for group in ranked["ranked_results"]:
            for hit in group.get("results", []):
                key = hit.get("doi") or f"{hit.get('source')}:{hit.get('source_id')}"
                if key in seen:
                    continue
                seen.add(key)
                unique_hits.append(hit)
        export_bibtex(bibtex_path, unique_hits)

    payload = {
        "output_dir": str(output_dir),
        "paper_hits_json": str(paper_hits_path),
        "shortlist_json": str(shortlist_json_path),
        "shortlist_txt": str(shortlist_txt_path),
        "shortlist_bib": str(bibtex_path) if bibtex_path else None,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
