# Support: Manuscript Context

Use this file only when the first problem is locating the real manuscript source or distinguishing source from rendered output.

## Use When

- the repository has several `.qmd` files and the active manuscript is unclear
- `docs/` or another output directory might be confused with source
- writing and figure work both need the same manuscript map

## First Move

Run:

```bash
python scripts/map_manuscript.py <repo-or-manuscript-dir> --pretty
```

Build a compact working map that identifies:

- likely primary manuscript file
- supporting section files
- bibliography and CSL files
- include files such as `preamble.tex`
- auxiliary notes or presentation `.qmd` files
- render-like directories such as `docs/`, `_site/`, `_freeze/`, `site_libs/`, or `*_files/`

## Load Next Only If

- load `references/route-writing.md` when the task is text editing or citation-gap extraction
- load `references/route-figures.md` when the task is figure creation or revision
- load `references/route-citations.md` when the task is literature search or claim support

## Return To Root When

- the manuscript source is clear enough that one route dominates
