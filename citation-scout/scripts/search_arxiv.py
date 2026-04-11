#!/usr/bin/env python3
"""Search arXiv and return metadata plus abstracts."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from typing import Any

from common import fetch_text, infer_paper_kind, informative_tokens, normalize_whitespace

ARXIV_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return normalize_whitespace("".join(node.itertext()))


def build_arxiv_query(query_text: str) -> str:
    tokens = informative_tokens(query_text)[:8]
    if not tokens:
        tokens = ["paper"]
    return "+AND+".join(f"all:{token}" for token in tokens)


def parse_arxiv_feed(feed_text: str, query_text: str, claim_id: str | None = None) -> list[dict[str, Any]]:
    root = ET.fromstring(feed_text)
    hits: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        entry_id = _text(entry.find("atom:id", ATOM_NS))
        title = _text(entry.find("atom:title", ATOM_NS))
        abstract = _text(entry.find("atom:summary", ATOM_NS))
        authors = [_text(node.find("atom:name", ATOM_NS)) for node in entry.findall("atom:author", ATOM_NS)]
        categories = [node.attrib.get("term", "") for node in entry.findall("atom:category", ATOM_NS) if node.attrib.get("term")]
        published = _text(entry.find("atom:published", ATOM_NS))
        year = published[:4] if published else ""
        doi = _text(entry.find("arxiv:doi", ATOM_NS))
        venue = _text(entry.find("arxiv:journal_ref", ATOM_NS)) or "arXiv"

        html_url = entry_id
        for link in entry.findall("atom:link", ATOM_NS):
            if link.attrib.get("rel") == "alternate":
                html_url = link.attrib.get("href", html_url)
                break

        source_id = entry_id.rsplit("/", 1)[-1]
        source_id = re.sub(r"v\d+$", "", source_id)
        hit = {
            "source": "arxiv",
            "source_id": source_id,
            "title": title,
            "authors": [author for author in authors if author],
            "year": year,
            "date": published,
            "venue": venue,
            "abstract": abstract,
            "url": html_url,
            "doi": doi,
            "categories": categories,
            "publication_types": [],
            "paper_kind": "",
            "query_text": query_text,
            "claim_id": claim_id,
        }
        hit["paper_kind"] = infer_paper_kind(hit)
        hits.append(hit)
    return hits


def search_arxiv(query_text: str, *, top_k: int = 8, claim_id: str | None = None) -> list[dict[str, Any]]:
    params = {
        "search_query": build_arxiv_query(query_text),
        "start": 0,
        "max_results": top_k,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    feed_text = fetch_text(ARXIV_URL, params=params)
    return parse_arxiv_feed(feed_text, query_text, claim_id=claim_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="arXiv query text")
    parser.add_argument("--top-k", type=int, default=8, help="Maximum papers to request")
    parser.add_argument("--claim-id", default=None, help="Optional claim identifier")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    hits = search_arxiv(args.query, top_k=args.top_k, claim_id=args.claim_id)
    payload = {
        "source": "arxiv",
        "query": args.query,
        "claim_id": args.claim_id,
        "hits": hits,
    }
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
