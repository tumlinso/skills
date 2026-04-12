# Route: Writing

Use this route for manuscript prose, structure, and citation-gap extraction.

## Use When

- editing or tightening `.qmd` prose
- splitting or reorganizing manuscript sections
- identifying likely citation gaps
- distinguishing source files from rendered Quarto output

## First Move

Run the manuscript mapper first if the source is not already obvious:

```bash
python scripts/map_manuscript.py <repo-or-manuscript-dir> --pretty
```

Then narrow the working set to the active manuscript file plus directly related section files.

## Load Next Only If

- use `scripts/extract_citation_gaps.py <repo-or-manuscript-dir> --pretty` when the next step is structured claim support work
- load `references/support-manuscript-context.md` if `docs/` or split sections make the source ambiguous
- return to the root skill and switch to `references/route-figures.md` if the user pivots into figure work
- return to the root skill and switch to `references/route-citations.md` if the user wants literature search rather than prose edits

## Writing Rules

- preserve front matter, labels, citations, and references unless structural change is requested
- keep edits local when a small section rewrite will do
- preserve the repository's existing include or section split conventions
- summarize changes in manuscript terms, not repository terms

## Return To Root When

- prose edits are done and the next bottleneck is figures or citation search
