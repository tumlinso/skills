#!/usr/bin/env python3
"""Export BibTeX for shortlisted quarto-manuscript papers."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import build_bibtex_entry, read_json, write_text


def load_shortlisted_hits(path: Path) -> list[dict]:
    payload = read_json(path)
    if isinstance(payload, dict) and "shortlist" in payload:
        groups = payload["shortlist"]
    elif isinstance(payload, dict) and "ranked_results" in payload:
        groups = payload["ranked_results"]
    else:
        raise ValueError(f"Unsupported shortlist payload in {path}")

    unique: dict[str, dict] = {}
    for group in groups:
        for hit in group.get("results", []):
            key = hit.get("doi") or f"{hit.get('source')}:{hit.get('source_id')}"
            unique.setdefault(key, hit)
    return list(unique.values())


def export_bibtex(path: Path, hits: list[dict]) -> None:
    entries = [build_bibtex_entry(hit, index=index) for index, hit in enumerate(hits, start=1)]
    write_text(path, "\n\n".join(entries))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Shortlist or ranked-results JSON")
    parser.add_argument("--output", required=True, help="Output .bib path")
    args = parser.parse_args()

    export_bibtex(Path(args.output), load_shortlisted_hits(Path(args.input)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
