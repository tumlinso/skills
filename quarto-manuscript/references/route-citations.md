# Route: Citations

Use this route for abstract-first citation support and shortlisting.

## Use When

- finding papers that support a claim
- searching PubMed, bioRxiv, or arXiv for a topic
- turning citation gaps into a shortlist
- exporting optional BibTeX from shortlisted papers

## First Move

Start with one compact shortlist run:

```bash
python scripts/build_citation_shortlist.py \
  --input <citation-gaps.json-or-manuscript-path> \
  --sources pubmed,biorxiv,arxiv \
  --top-k 5 \
  --output-dir /tmp/citation_scout_run \
  --emit-bibtex
```

Or, for a free-form topic:

```bash
python scripts/build_citation_shortlist.py \
  --query "single-cell atlas benchmark integration methods" \
  --sources pubmed,biorxiv,arxiv \
  --top-k 5 \
  --output-dir /tmp/citation_scout_run \
  --emit-bibtex
```

Read `shortlist.txt` first. Only inspect raw abstracts or JSON outputs if the shortlist is weak or ambiguous.

## Load Next Only If

- load `references/citations/search-boundaries.md` when source coverage or confidence needs explanation
- return to the root skill and switch to `references/route-writing.md` when the user wants manuscript revisions after the shortlist

## Execution Rules

- keep the workflow abstract-first and summary-first
- do not fetch or summarize full PDFs by default
- do not read every returned abstract into context
- be explicit about which sources were searched and whether the answer came from shortlist summaries or raw abstracts

## Return To Root When

- the shortlist is stable and the next task becomes writing or figure work
