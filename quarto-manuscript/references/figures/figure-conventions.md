# Figure Conventions

Follow existing repository conventions first. Only propose a new layout when the manuscript repo has no clear figure structure.

## Preferred Detection Order

1. Existing figure roots such as `figures/`, `figs/`, `plots/`, or `assets/figures/`
2. Existing subdirectories for generated outputs, scripts, specs, or captions
3. Minimal fallback layout rooted at `figures/`

## Minimal Fallback Layout

When no figure convention exists, use:

```text
figures/
  generated/
    data/
    schematics/
  scripts/
    data/
    schematics/
  specs/
  captions/
```

Do not force this layout when the repo already has a clearer convention.

## Reproducibility Expectations

Every figure should have:

- a stable `figure_id`
- a spec JSON describing mode, inputs, parameters, outputs, and manuscript context
- a source artifact that can regenerate exported outputs
- exported assets in manuscript-friendly formats

For `data-figure` mode:

- store the plotting script explicitly
- record repo-local input paths in the spec
- keep plot parameters explicit rather than hidden in a notebook state

For `schematic-figure` mode:

- keep a structured spec describing nodes, panels, labels, arrows, or text description
- preserve an editable SVG or equivalent vector-first artifact where practical

## Output Policy

Default export set:

- `svg`
- `png`

Add `pdf` when:

- the repo already uses PDF figure assets
- the user asks for it
- the rendering path can support it cleanly

## Caption Scaffolding

Caption scaffolding is optional and lightweight.

If helpful, store one caption stub per figure under the detected caption directory. Keep it figure-specific. Do not rewrite manuscript prose around the figure unless the user explicitly asks for manuscript editing.
