---
name: quarto-paper
description: Writing assistant for Quarto manuscripts, preprints, and article-style `.qmd` projects. Use when Codex needs to detect the real manuscript source in a Quarto repo, inspect `_quarto.yml` and manuscript `.qmd` structure, distinguish source files from rendered output such as `docs/`, revise prose section-by-section, split a large manuscript into smaller subsection files while preserving front matter and references, or prepare structured citation-gap notes for later handoff to abstract-first literature scouting. Default skill for Quarto manuscript editing. Do not use for generic Quarto websites or books unless the task is clearly manuscript-centered, and do not use for dataset intake, heavy download workflows, downstream analysis, or broad research-agent work.
---

# Quarto Paper

Use this as the default skill for Quarto manuscript editing.

Keep the workflow manuscript-focused. Treat manuscript files as the working context, and treat rendered output as non-source until the repository proves otherwise.

## Core Rules

- Detect the manuscript before editing prose.
- Inspect `_quarto.yml` when it exists, but do not require it.
- Prefer the real manuscript source files over broad repo-wide editing.
- Do not assume `docs/` is source just because it exists.
- Preserve front matter, section order, labels, citations, and references unless the user asks for structural change.
- Keep companion-skill handoffs optional and advisory.
- Do not trigger dataset search, downloads, or generic research workflows for ordinary writing tasks.

## Trigger Boundary

Use this skill when the task is any of:

- editing or tightening manuscript prose in `.qmd` files
- understanding the structure of a Quarto paper, preprint, or article project
- identifying the primary manuscript file and related section files
- splitting a large manuscript `.qmd` into smaller subsection files
- reorganizing sections while preserving Quarto structure
- checking likely citation gaps in manuscript prose
- distinguishing source files from rendered Quarto output

Do not use this skill when the task is primarily:

- generic Quarto website, blog, or book work without a manuscript focus
- heavy literature search, bibliography expansion, or network-first citation hunting
- dataset search, public data intake, download orchestration, or data cleaning
- downstream analysis, figure generation, or computational pipeline work

If a companion skill exists locally and the task truly changes domains, recommend it explicitly. Do not fail when that skill is absent.

## Opening Pass

Start with a manuscript map before changing prose.

Use:

```bash
python scripts/map_manuscript.py <repo-or-manuscript-dir> --pretty
```

Build a working map that identifies:

- likely primary manuscript file
- supporting section files
- bibliography files
- CSL files
- include files such as `preamble.tex`
- auxiliary `.qmd` files such as notes or presentations
- render-like directories such as `docs/`, `_site/`, `site_libs/`, `_freeze/`, or `*_files/`

Prefer evidence over guesses. Root-level `.qmd` files with manuscript front matter usually outrank notes, presentations, and subsection fragments.

## Manuscript Detection

Inspect in this order:

1. `_quarto.yml`
2. root-level or manuscript-root `.qmd` files
3. split section directories such as `sections/`, `chapters/`, or underscore-prefixed subsection files
4. bibliography, CSL, and include files referenced from front matter
5. render-like directories

When deciding whether a file is source:

- prefer `.qmd` files with title or author front matter, article or pdf format, bibliography or CSL metadata, and manuscript headings such as Introduction, Methods, Results, Discussion, or References
- demote `.qmd` files in `notes/`, `presentation/`, `slides/`, or similar auxiliary paths
- demote underscore-prefixed subsection files as primary-manuscript candidates unless the repo already uses them as the main structure
- treat `references.qmd` as supporting material, not the main manuscript

For `docs/`:

- classify it as output if `_quarto.yml` points `output-dir` at `docs` or if `docs/` mostly contains rendered HTML, PDF, assets, or `site_libs`
- classify it as source only when the manuscript itself lives there or project files clearly route source through it
- otherwise mark it ambiguous and do not edit it as manuscript source by default

## Writing Workflow

After the manuscript map is clear:

1. narrow the working set to the active manuscript file plus directly related section files
2. read the relevant section before rewriting it
3. preserve manuscript voice, notation, labels, and nearby argument flow
4. edit one section or local structure at a time
5. summarize what changed in manuscript terms, not repo terms

Prefer these operations:

- tighten prose
- remove repetition
- improve transitions
- clarify claims and limitations
- move paragraphs or subsections cleanly
- normalize section-level tone and terminology

Avoid broad multi-file churn when a local edit will do.

## Large-File Splitting

Support manual, manuscript-safe splitting of large `.qmd` files.

Before splitting:

1. identify the real top-level manuscript file
2. identify heading boundaries that match the current argument structure
3. confirm where bibliography, CSL, and include metadata live

When splitting:

- keep YAML front matter only in the top-level manuscript file
- move body content along existing heading boundaries
- preserve section titles, labels, citations, footnotes, callouts, and cross-references
- reuse an existing `sections/` or similar structure if the repo already has one
- if no split structure exists, create the smallest compatible structure rather than inventing a new manuscript system
- keep the top-level manuscript as the orchestrator for order and global metadata

Do not move bibliography, CSL, or preamble metadata into subsection files unless the repository already does that and Quarto requires it.

If include syntax is not already established in the repo, stay conservative: split deliberately, keep the top-level file readable, and prefer the repository's existing manuscript conventions over introducing a new include style on speculation.

## Citation-Gap Assistance

Use:

```bash
python scripts/extract_citation_gaps.py <repo-or-manuscript-dir> --pretty
```

Look for likely unsupported claims such as:

- epidemiologic or prevalence statements
- mortality or clinical-impact claims
- mechanistic biological claims
- comparative or novelty claims
- broad consensus statements
- method capability claims that read as literature-backed rather than purely authorial framing

Prepare citation-gap output with:

- file path
- heading context
- line number
- claim text
- reason the claim likely needs support
- suggested citation type

If `citation-scout` exists locally, recommend it after preparing this manuscript-side list. Pass the citation-gap JSON forward instead of re-reading the whole manuscript there. If it does not exist, still finish the citation-gap preparation work here.

## Optional Handoffs

This skill is the manuscript orchestrator. Keep handoffs optional.

If companion skills exist:

- suggest `citation-scout` for abstract-first literature search, compact shortlisting, and optional BibTeX export after citation gaps are prepared
- suggest `dataset-intake` only when the user explicitly pivots from manuscript writing to public dataset search
- suggest `quarto-lint` only when the task becomes render validation or deeper Quarto-specific linting

Before suggesting a handoff, confirm that the companion skill actually exists in the local skill list. If it does not, continue within `quarto-paper`.

## Helper Scripts

- `scripts/map_manuscript.py`: map candidate manuscript files, section files, supporting bibliography or CSL or include files, and the likely role of `docs/`
- `scripts/extract_citation_gaps.py`: extract likely unsupported claims from manuscript prose into structured output

Use the scripts to reduce discovery cost, not to replace judgment. The skill still needs to read the manuscript sections it edits.
