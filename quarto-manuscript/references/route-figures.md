# Route: Figures

Use this route for manuscript figures only.

## Use When

- creating or revising data figures
- creating or revising schematic figures
- exporting manuscript-ready assets
- updating figure specs, scripts, or output placement

## First Move

Detect manuscript and figure context first:

```bash
python scripts/detect_figure_context.py <repo-or-manuscript-dir> --pretty
```

Then classify the task as `data-figure` or `schematic-figure`.

## Load Next Only If

- load `references/figures/figure-conventions.md` when output layout or reproducibility conventions need clarification
- load `references/figures/examples.md` when the user request is structurally similar to an existing example
- return to the root skill and switch to `references/route-writing.md` if the task becomes prose editing

## Execution Rules

- prefer repo-local processed inputs and result tables over new analysis
- create or revise the figure spec before re-exporting assets
- preserve figure identity and output paths unless the user asks for a new figure
- keep figure work separate from manuscript prose unless the user asks for caption or text changes

## Return To Root When

- the figure artifacts are stable and the next task is prose or citation work
