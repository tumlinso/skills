#!/usr/bin/env python3
"""Search PubMed and return metadata plus abstracts."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from typing import Any

from common import fetch_json, fetch_text, infer_paper_kind, maybe_int, normalize_whitespace

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return normalize_whitespace("".join(node.itertext()))


def parse_pubmed_xml(xml_text: str, query_text: str, claim_id: str | None = None) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    hits: list[dict[str, Any]] = []
    for article in root.findall(".//PubmedArticle"):
        citation = article.find("./MedlineCitation")
        article_node = citation.find("./Article") if citation is not None else None
        pubmed_data = article.find("./PubmedData")
        if citation is None or article_node is None or pubmed_data is None:
            continue

        pmid = _text(citation.find("./PMID"))
        title = _text(article_node.find("./ArticleTitle"))
        abstract_parts = []
        for abstract_text in article_node.findall("./Abstract/AbstractText"):
            label = abstract_text.attrib.get("Label")
            text = _text(abstract_text)
            if not text:
                continue
            abstract_parts.append(f"{label}: {text}" if label else text)
        abstract = normalize_whitespace(" ".join(abstract_parts))

        authors = []
        for author in article_node.findall("./AuthorList/Author"):
            collective = _text(author.find("./CollectiveName"))
            if collective:
                authors.append(collective)
                continue
            last = _text(author.find("./LastName"))
            fore = _text(author.find("./ForeName"))
            name = normalize_whitespace(f"{fore} {last}")
            if name:
                authors.append(name)

        journal = _text(article_node.find("./Journal/Title"))
        publication_types = [_text(node) for node in article_node.findall("./PublicationTypeList/PublicationType") if _text(node)]
        doi = ""
        for article_id in pubmed_data.findall("./ArticleIdList/ArticleId"):
            if article_id.attrib.get("IdType") == "doi":
                doi = normalize_whitespace(article_id.text or "")
                break

        year = ""
        date_value = ""
        for path in (
            "./Article/Journal/JournalIssue/PubDate/Year",
            "./Article/ArticleDate/Year",
            "./DateCompleted/Year",
        ):
            text = _text(citation.find(path))
            if text:
                year = text
                break
        month = _text(citation.find("./Article/Journal/JournalIssue/PubDate/Month"))
        day = _text(citation.find("./Article/Journal/JournalIssue/PubDate/Day"))
        if year:
            pieces = [year]
            if month:
                pieces.append(month)
            if day:
                pieces.append(day)
            date_value = "-".join(pieces)

        hit = {
            "source": "pubmed",
            "source_id": pmid,
            "title": title,
            "authors": authors,
            "year": year,
            "date": date_value,
            "venue": journal,
            "abstract": abstract,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            "doi": doi,
            "categories": publication_types,
            "publication_types": publication_types,
            "paper_kind": "",
            "query_text": query_text,
            "claim_id": claim_id,
        }
        hit["paper_kind"] = infer_paper_kind(hit)
        hits.append(hit)
    return hits


def search_pubmed(query_text: str, *, top_k: int = 8, claim_id: str | None = None, email: str | None = None) -> list[dict[str, Any]]:
    params = {
        "db": "pubmed",
        "retmode": "json",
        "retmax": top_k,
        "sort": "relevance",
        "term": query_text,
        "tool": "citation-scout",
    }
    if email:
        params["email"] = email
    search_payload = fetch_json(ESEARCH_URL, params=params)
    ids = search_payload.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    xml_text = fetch_text(
        EFETCH_URL,
        params={
            "db": "pubmed",
            "retmode": "xml",
            "id": ",".join(ids),
            "tool": "citation-scout",
            **({"email": email} if email else {}),
        },
    )
    return parse_pubmed_xml(xml_text, query_text, claim_id=claim_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="PubMed query text")
    parser.add_argument("--top-k", type=int, default=8, help="Maximum papers to request")
    parser.add_argument("--claim-id", default=None, help="Optional claim identifier")
    parser.add_argument("--email", default=None, help="Optional email for NCBI etiquette")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    hits = search_pubmed(args.query, top_k=args.top_k, claim_id=args.claim_id, email=args.email)
    payload = {
        "source": "pubmed",
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
