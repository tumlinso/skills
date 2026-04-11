---
name: public-omics-intake
description: Discover, rank, plan, and fetch public omics datasets for reproducible intake workflows. Use when Codex needs to find GEO or SRA studies relevant to a biological system, search public metadata for candidate datasets, rank studies for likely integratability, build machine-readable manifests, plan a canonical on-disk dataset layout, or fetch metadata, processed matrices, supplementary files, or explicitly requested raw SRA runs. Do not use this skill for downstream analysis, normalization, differential expression, alignment, quantification, AnnData construction, or generic literature review that is not directly tied to public dataset acquisition.
---

# Public Omics Intake

Use this skill for public dataset discovery and acquisition only.

Default to metadata-first discovery and processed-file acquisition first. Do not default to raw SRA downloads.

Keep the workflow narrow and reproducible:

1. parse the request
2. query GEO and or SRA metadata
3. rank candidates for integratability
4. show assumptions and candidate list
5. ask exactly once for the dataset root before any filesystem changes
6. plan the canonical layout and fetch scope
7. write manifests and provenance
8. fetch only the requested public layer

## Hard Boundaries

- Do not normalize, align, quantify, integrate, or build AnnData objects.
- Do not start downloads immediately after a biological description.
- Do not create directories until the user has provided the destination root.
- Do not fetch raw SRA data unless the user explicitly requests raw or all-public scope.
- Do not use brittle HTML scraping when official programmatic GEO or SRA access exists.

## Parse The Request

Turn the freeform description into a structured request object before searching.

Capture these fields when possible:

- `biological_system`
- `organisms`
- `developmental_stages`
- `disease_state`
- `tissues`
- `cell_type`
- `preferred_modalities`
- `required_modalities`
- `processed_files_acceptable`
- `raw_files_required`
- `public_only_required`
- `intended_use`
- `perturbation`

If the request is ambiguous, make a reasonable first-pass query spec and state the assumptions instead of blocking.

Use:

- `scripts/query_geo.py --description ... --query-spec-json ...`
- `scripts/query_sra.py --description ... --query-spec-json ...`

## Metadata Discovery

Search metadata sources first. Keep GEO and SRA discovery separate from fetch.

Use `scripts/query_geo.py` for:

- GEO accession-driven lookup
- free-text GEO discovery
- normalized study-level GEO records
- candidate GEO download locations using stable GEO FTP path rules

Use `scripts/query_sra.py` for:

- SRA or BioProject or run-driven lookup
- free-text SRA discovery
- normalized study-level SRA records
- separate run metadata tables

Return a concise summary of assumptions plus a ranked candidate list before proposing any download plan.

## Candidate Ranking

Rank candidates for likely integratability, not just lexical relevance.

Use `scripts/rank_candidates.py` with `scripts/default_ranking_weights.json`.

Score at minimum:

- species match
- stage or temporal coverage match
- modality match
- assay or chemistry compatibility
- availability of processed matrices
- availability of raw files
- richness of sample metadata
- completeness of linked study or sample or run accessions
- public accessibility
- likely ease of integration
- identifier consistency across files and layers

Always return:

- scalar `integratability_score`
- factor-by-factor breakdown
- short rationale lines

Read `references/ranking_rules.md` if you need the intended semantics.

## Destination Root Rule

Before any filesystem-changing or download action, confirm the destination root.

If the user has not supplied it yet, stop and ask exactly once:

`Where should the dataset root live?`

Do not create directories, manifests, links, or downloaded files before the user answers that question.

## Layout Planning And Manifests

After a root is provided, plan the canonical layout first.

Use `scripts/plan_layout.py --dry-run` to emit a concrete directory plan under:

```text
<DATA_ROOT>/
  registry/
    searches/
    manifests/
    plans/
    provenance/
  sources/
    geo/
    sra/
  projects/
    <project_name>/
  tmp/
```

Keep `sources/` canonical and reusable. Keep `projects/` lightweight.

After ranking and selection:

- use `scripts/build_manifest.py` to write machine-readable dataset manifests
- use `scripts/link_project.py` to create project-local selection files and lightweight links

Expected machine-readable outputs:

- structured query spec JSON
- candidate list JSON and TSV
- selected dataset manifest JSON
- file manifest JSON
- fetch plan JSON
- provenance log JSONL

## Fetch Policy

Fetch only the public data layer the user currently wants.

Scopes:

- `metadata`
- `processed`
- `raw`
- `all-public`

Defaults:

- if raw versus processed is unspecified, default to metadata plus processed candidates first
- for GEO, prefer `metadata` or `processed`
- for SRA, prefer `metadata` until raw is explicitly requested

Use:

- `scripts/fetch_geo.py` for metadata, processed matrices, or supplementary GEO files
- `scripts/fetch_sra.py` for SRA metadata and explicit raw run acquisition

`fetch_sra.py` may use `prefetch` and optionally `fasterq-dump`, but only when raw scope is explicit.

## Output Requirements

Return both:

- a readable summary with assumptions, candidate highlights, selected accessions, fetch scope, and next actions
- machine-readable output paths

Be explicit about:

- what was inferred versus directly specified
- whether the result is metadata-only, processed-first, raw, or all-public
- whether raw downloads were intentionally skipped
- which GEO or SRA accessions are linked across study, sample, and run layers

## Reference Map

- Read `references/examples.md` for realistic invocation patterns.
- Read `references/ranking_rules.md` for scoring semantics and weight intent.
- Read `references/geo_notes.md` for GEO-specific discovery and fetch rules.
- Read `references/sra_notes.md` for SRA-specific discovery and raw-download guardrails.
