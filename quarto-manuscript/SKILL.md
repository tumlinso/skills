---
name: quarto-manuscript
description: >-
  Unified Quarto manuscript skill for article-style `.qmd` projects. Use when
  Codex needs to detect the real manuscript source, revise prose, reorganize
  section files, create or revise manuscript figures, prepare citation-gap
  notes, or run abstract-first citation shortlisting without treating rendered
  output as source. Keep the workflow routed: choose writing, figures, or
  citations first, load only that route, and keep references one hop from this
  entry skill.
---

# Quarto Manuscript

Use this as the public entry point for Quarto manuscript work.

Do not load every route. Detect manuscript context once, choose one path, and load only that route file first.

Keep manuscript work source-first:

- treat rendered output as non-source until the repository proves otherwise
- preserve the repository's existing manuscript and figure layout when possible
- keep writing, figures, and citations as separate routes even when they live under one skill
- prefer repo-local artifacts before downloads, broad research, or upstream reprocessing

## Choose Your Path

Choose the first statement that is true. Load only the file named in that row first.

| If the task sounds like... | Start here | Then load only if needed |
| --- | --- | --- |
| "Find the real manuscript", "tighten prose", "split or reorganize sections", "check citation gaps in the text" | `references/route-writing.md` | `references/support-manuscript-context.md` when repo structure is ambiguous |
| "Make or revise a figure", "export manuscript-ready assets", "build a schematic or data plot" | `references/route-figures.md` | `references/figures/figure-conventions.md` and `references/figures/examples.md` after figure mode is clear |
| "Find papers for this claim", "turn citation gaps into a shortlist", "search abstracts only" | `references/route-citations.md` | `references/citations/search-boundaries.md` when source coverage or confidence is unclear |
| "I need general manuscript context first" | `references/support-manuscript-context.md` | one route above once the active task is obvious |

## Opening Moves

After choosing a path, do only that path's opening move before loading more references.

## Shared Context Rule

All three routes may need the same manuscript map. Reuse that context instead of re-discovering the repo each time.

Use:

```bash
python scripts/map_manuscript.py <repo-or-manuscript-dir> --pretty
```

Only run figure or citation scripts after the manuscript path or query target is clear enough to avoid broad scanning.

## Common Sequences

- `references/route-writing.md` -> `references/route-citations.md`: extract likely unsupported claims first, then build a compact shortlist.
- `references/route-writing.md` -> `references/route-figures.md`: detect manuscript source first, then preserve the repo's figure conventions.
- `references/route-citations.md` -> `references/route-writing.md`: shortlist papers first, then revise the text with that evidence in mind.

## Script Map

- `scripts/map_manuscript.py`: detect the likely manuscript source and supporting files.
- `scripts/extract_citation_gaps.py`: extract likely unsupported claims from manuscript prose.
- `scripts/detect_figure_context.py`: detect figure layout, manuscript file, and likely output roots.
- `scripts/make_data_figure.py`: build reproducible figures from repo-local tables or matrices.
- `scripts/make_schematic_figure.py`: build editable schematic figures from structured descriptions.
- `scripts/update_figure_spec.py`: revise a figure spec without changing figure identity.
- `scripts/export_figure_assets.py`: regenerate exports from a figure spec.
- `scripts/build_citation_shortlist.py`: run the end-to-end abstract-first shortlist workflow.
- `scripts/search_pubmed.py`, `scripts/search_biorxiv.py`, `scripts/search_arxiv.py`: source-specific metadata and abstract search helpers.
- `scripts/normalize_paper_hits.py`, `scripts/rank_paper_hits.py`, `scripts/export_bibtex.py`: shortlist normalization, ranking, and optional BibTeX export.

## Hard Boundaries

- Do not treat this as a generic Quarto website or blog skill.
- Do not default to dataset search or download workflows.
- Do not read every manuscript file, figure artifact, or abstract into context by default.
- Do not rewrite prose while doing figure-only work unless the user asks for that next step.
- Do not fetch or summarize full PDFs by default.
