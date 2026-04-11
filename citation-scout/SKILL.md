---
name: citation-scout
description: Companion skill for abstract-first literature scouting, manuscript claim support, and compact citation shortlisting. Use when Codex needs to search PubMed, bioRxiv, or arXiv for papers relevant to a manuscript claim, citation-gap list, methods section, benchmark framing, or free-form research topic; rank hits against the claim or topic; read metadata and abstracts only; export compact shortlist summaries and optional BibTeX; or suggest how candidate papers could fit into an introduction, methods, results, or discussion section. Do not use this skill for full-text PDF reading, broad autonomous research crawling, or generic manuscript editing that does not need literature search.
---

# Citation Scout

Use this as the literature-search companion for manuscript and methods work.

Keep the workflow abstract-first and summary-first:

1. take a claim, citation-gap list, manuscript path, or topic query
2. search a small set of sources
3. normalize and rank metadata plus abstracts
4. read the compact shortlist summary first
5. inspect raw abstracts only when the shortlist is ambiguous

## Hard Boundaries

- Do not fetch or summarize full PDFs in v1.
- Do not turn this into a broad internet-research agent.
- Do not read every returned abstract into context by default.
- Do not claim that bioRxiv offers a true full-archive free-text API when it does not.
- Do not choose and insert manuscript citations automatically unless the user asks for that next step.

## Best Entry Modes

Use this skill when the task is any of:

- "find papers that support this claim"
- "search PubMed, bioRxiv, or arXiv for this topic"
- "turn citation gaps into a shortlist"
- "help me think through what literature belongs in the intro, methods, results, or discussion"
- "give me abstract-only candidate papers plus BibTeX"

For manuscript-linked work, prefer these inputs:

- `quarto-paper/scripts/extract_citation_gaps.py` JSON output
- a manuscript `.qmd` file or manuscript directory
- a direct topic or method question when the user is still brainstorming

## Opening Workflow

Start with one compact run of:

```bash
python scripts/build_citation_shortlist.py \
  --input <citation-gaps.json-or-manuscript-path> \
  --sources pubmed,biorxiv,arxiv \
  --top-k 5 \
  --output-dir /tmp/citation_scout_run \
  --emit-bibtex
```

Or for a free-form topic:

```bash
python scripts/build_citation_shortlist.py \
  --query "single-cell atlas benchmark integration methods" \
  --sources pubmed,biorxiv,arxiv \
  --top-k 5 \
  --output-dir /tmp/citation_scout_run \
  --emit-bibtex
```

Read `shortlist.txt` first. Only load `shortlist.json` or raw `paper_hits.json` if the ranking looks weak or the user wants deeper reasoning.

## Output Requirements

Be explicit about:

- whether the input was manuscript-linked or topic-only
- which sources were searched
- whether the answer came from compact shortlist summaries or raw abstracts
- which papers are likely review, primary, or preprint
- which papers support background framing, methods precedent, mechanistic support, or benchmark comparison
- when a source limitation affects confidence, especially for bioRxiv search

## Reference Map

- Read `references/search-boundaries.md` for source-specific strengths and limits.

## Script Map

- `scripts/search_pubmed.py`: query PubMed and return metadata plus abstracts.
- `scripts/search_biorxiv.py`: scan recent bioRxiv metadata windows and locally rank abstract matches.
- `scripts/search_arxiv.py`: query arXiv and return metadata plus abstracts.
- `scripts/normalize_paper_hits.py`: merge source outputs into one normalized hit set.
- `scripts/rank_paper_hits.py`: score hits against claims or topics.
- `scripts/build_citation_shortlist.py`: end-to-end claim or topic workflow that emits `paper_hits.json`, `shortlist.json`, `shortlist.txt`, and optional `shortlist.bib`.
- `scripts/export_bibtex.py`: export BibTeX for shortlisted papers.

## Handoff Notes

- From `quarto-paper`, use this skill after manuscript detection or citation-gap extraction is already done.
- If the user returns to writing or section revision, hand back to `quarto-paper`.
