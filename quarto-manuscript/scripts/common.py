#!/usr/bin/env python3
"""Shared utilities for quarto-manuscript citation scripts."""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "with",
}

METHOD_WORDS = {
    "algorithm",
    "architecture",
    "atlas",
    "benchmark",
    "dataset",
    "decoder",
    "embedding",
    "error",
    "framework",
    "integration",
    "latent",
    "learning",
    "loss",
    "method",
    "model",
    "pipeline",
    "prediction",
    "pretrain",
    "representation",
    "scaffold",
    "single-cell",
    "transformer",
}

MECHANISTIC_WORDS = {
    "activates",
    "associated",
    "attenuates",
    "binds",
    "causes",
    "drives",
    "enables",
    "induces",
    "inhibits",
    "pathway",
    "promotes",
    "regulates",
    "suppresses",
}

BACKGROUND_WORDS = {
    "common",
    "consensus",
    "developmental",
    "disease",
    "epidemiology",
    "mortality",
    "prevalence",
    "review",
    "widely",
}

BENCHMARK_WORDS = {
    "accuracy",
    "benchmark",
    "compare",
    "comparison",
    "dataset",
    "error",
    "faster",
    "improves",
    "outperforms",
    "performance",
    "reduces",
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9+./-]*", (text or "").lower())


def informative_tokens(text: str) -> list[str]:
    return [token for token in tokenize(text) if token not in STOPWORDS and len(token) > 2]


def normalized_title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "item"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any, *, pretty: bool = True) -> None:
    if pretty:
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_text(json.dumps(data, separators=(",", ":"), sort_keys=True), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def fetch_json(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    request_url = url
    if params:
        request_url = f"{url}?{urlencode(params, doseq=True)}"
    request = Request(
        request_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "quarto-manuscript/1.0 (+https://github.com/tumlinso/skills)",
            **(headers or {}),
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> str:
    request_url = url
    if params:
        request_url = f"{url}?{urlencode(params, doseq=True)}"
    request = Request(
        request_url,
        headers={
            "Accept": "*/*",
            "User-Agent": "quarto-manuscript/1.0 (+https://github.com/tumlinso/skills)",
            **(headers or {}),
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def classify_query_mode(claim: dict[str, Any]) -> str:
    sentence = (claim.get("sentence") or claim.get("query_text") or "").lower()
    suggestion = (claim.get("suggested_citation_type") or "").lower()
    reasons = " ".join(claim.get("reasons") or []).lower()
    token_set = set(informative_tokens(sentence))

    if "epidemiology" in suggestion or "historical" in suggestion:
        return "background"
    if "comparative" in suggestion or "benchmark" in suggestion or token_set.intersection(BENCHMARK_WORDS):
        return "benchmark"
    if "mechanistic" in suggestion or token_set.intersection(MECHANISTIC_WORDS):
        return "mechanistic"
    if "review" in suggestion or "consensus" in suggestion or token_set.intersection(BACKGROUND_WORDS) or "consensus" in reasons:
        return "background"
    if token_set.intersection(METHOD_WORDS):
        return "methods"
    return "general"


def infer_paper_kind(hit: dict[str, Any]) -> str:
    title = (hit.get("title") or "").lower()
    publication_types = " ".join(hit.get("publication_types") or []).lower()
    source = hit.get("source")
    if source in {"arxiv", "biorxiv"}:
        return "preprint"
    if "review" in publication_types or "review" in title or "survey" in title:
        return "review"
    return "primary"


def token_overlap_score(query_text: str, candidate_text: str) -> float:
    query_tokens = informative_tokens(query_text)
    if not query_tokens:
        return 0.0
    candidate_tokens = set(informative_tokens(candidate_text))
    if not candidate_tokens:
        return 0.0
    overlap = sum(1 for token in query_tokens if token in candidate_tokens)
    return overlap / len(query_tokens)


def freshness_boost(hit: dict[str, Any], query_mode: str) -> float:
    year = hit.get("year")
    if not year:
        return 0.0
    try:
        year_int = int(str(year)[:4])
    except ValueError:
        return 0.0
    age = max(0, date.today().year - year_int)
    if query_mode in {"methods", "benchmark"}:
        return max(0.0, 0.6 - min(age, 12) * 0.05)
    return max(0.0, 0.25 - min(age, 10) * 0.02)


def score_hit(claim: dict[str, Any], hit: dict[str, Any]) -> dict[str, Any]:
    query_mode = claim.get("query_mode") or classify_query_mode(claim)
    title_score = token_overlap_score(claim["query_text"], hit.get("title", ""))
    abstract_score = token_overlap_score(claim["query_text"], hit.get("abstract", ""))
    score = (title_score * 4.0) + (abstract_score * 3.0)

    source = hit.get("source")
    paper_kind = hit.get("paper_kind") or infer_paper_kind(hit)
    if query_mode == "background" and source == "pubmed":
        score += 0.6
    if query_mode in {"methods", "benchmark"} and source in {"arxiv", "biorxiv"}:
        score += 0.5
    if query_mode == "mechanistic" and source == "pubmed":
        score += 0.4
    if query_mode == "background" and paper_kind == "review":
        score += 0.7
    if query_mode == "mechanistic" and paper_kind in {"primary", "preprint"}:
        score += 0.3
    if query_mode in {"methods", "benchmark"} and any(
        word in ((hit.get("title") or "") + " " + (hit.get("abstract") or "")).lower()
        for word in ("benchmark", "dataset", "performance", "framework", "method")
    ):
        score += 0.4

    score += freshness_boost(hit, query_mode)
    return {
        "score": round(score, 4),
        "title_overlap": round(title_score, 4),
        "abstract_overlap": round(abstract_score, 4),
        "query_mode": query_mode,
        "paper_kind": paper_kind,
    }


def dedupe_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str | None, str], dict[str, Any]] = {}
    for hit in hits:
        key = (hit.get("claim_id"), (hit.get("doi") or normalized_title_key(hit.get("title", "")) or hit.get("source_id", "")))
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = hit
            continue
        if len(hit.get("abstract") or "") > len(existing.get("abstract") or ""):
            deduped[key] = hit
    return list(deduped.values())


def manuscript_role(claim: dict[str, Any], hit: dict[str, Any]) -> str:
    query_mode = claim.get("query_mode") or classify_query_mode(claim)
    heading = (claim.get("heading") or "").lower()
    if query_mode == "background":
        return "intro framing" if "intro" in heading else "background support"
    if query_mode == "mechanistic":
        return "results interpretation" if "results" in heading or "discussion" in heading else "mechanistic support"
    if query_mode == "benchmark":
        return "benchmark comparison"
    if query_mode == "methods":
        return "methods precedent"
    if hit.get("paper_kind") == "review":
        return "background support"
    return "general support"


def integration_note(claim: dict[str, Any], hit: dict[str, Any]) -> str:
    role = manuscript_role(claim, hit)
    sentence = normalize_whitespace(claim.get("sentence") or claim.get("query_text") or "")
    trimmed = sentence if len(sentence) <= 90 else sentence[:87].rstrip() + "..."
    kind = hit.get("paper_kind") or infer_paper_kind(hit)
    if role == "benchmark comparison":
        return f"Use in results or methods to position benchmark claims around: {trimmed}"
    if role == "methods precedent":
        return f"Use in methods framing to justify prior art or baseline context for: {trimmed}"
    if role == "mechanistic support":
        return f"Use as primary mechanistic support for: {trimmed}"
    if role == "results interpretation":
        return f"Use in discussion or results interpretation for: {trimmed}"
    if kind == "review":
        return f"Use as background or review anchor for: {trimmed}"
    return f"Use as supporting citation for: {trimmed}"


def summary_line(hit: dict[str, Any]) -> str:
    title = normalize_whitespace(hit.get("title", "Untitled"))
    venue = hit.get("venue") or hit.get("source", "")
    year = hit.get("year") or "n.d."
    why = hit.get("integration_note") or ""
    return f"{title} ({venue}, {year}) - {why}"


def build_bibtex_entry(hit: dict[str, Any], index: int = 1) -> str:
    doi = hit.get("doi")
    source_id = hit.get("source_id") or f"item{index}"
    author = " and ".join(hit.get("authors") or ["Unknown"])
    year = str(hit.get("year") or "n.d.")
    entry_key_root = safe_slug((hit.get("authors") or ["item"])[0].split()[-1])[:20]
    entry_key = f"{entry_key_root}{year if year.isdigit() else index}"
    title = (hit.get("title") or "Untitled").replace("{", "").replace("}", "")
    venue = (hit.get("venue") or hit.get("source") or "").replace("{", "").replace("}", "")
    url = hit.get("url") or ""
    lines = [
        f"@article{{{entry_key},",
        f"  title = {{{title}}},",
        f"  author = {{{author}}},",
        f"  year = {{{year}}},",
        f"  journal = {{{venue}}},",
        f"  url = {{{url}}},",
    ]
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    lines.append(f"  note = {{{hit.get('source', 'unknown')}:{source_id}}}")
    lines.append("}")
    return "\n".join(lines)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def recent_date_range(lookback_days: int) -> tuple[str, str]:
    end_date = date.today()
    start_date = end_date - timedelta(days=max(1, lookback_days))
    return start_date.isoformat(), end_date.isoformat()


def maybe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
