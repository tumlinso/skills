# Quarto Figures Examples

Use these examples to keep `quarto-manuscript` scoped to manuscript figure work.

## Data-Figure Examples

- "Create a volcano plot for the Results section from `results/dge/fibroblasts.csv` and save manuscript-ready assets."
- "Make a UMAP-style scatter plot from `analysis/embedding.tsv` with cell type as the color grouping."
- "Revise Figure 2 to change the palette and export SVG, PNG, and PDF."
- "Generate a multi-panel bar-and-line summary figure from the processed QC tables already in this repo."

Example helper flow:

```bash
python scripts/detect_figure_context.py /path/to/repo --input results/dge/fibroblasts.csv --pretty

python scripts/make_data_figure.py \
  --repo /path/to/repo \
  --figure-id fig2-volcano \
  --input results/dge/fibroblasts.csv \
  --plot-kind scatter \
  --x log2_fold_change \
  --y neg_log10_padj \
  --label gene \
  --title "Fibroblast differential expression"
```

## Schematic-Figure Examples

- "Build a workflow diagram for the Introduction figure showing sample collection, sequencing, preprocessing, integration, and downstream modeling."
- "Create a conceptual study schematic with three panels: cohort design, perturbation experiment, and outcome readout."
- "Revise the workflow diagram so the inference step is highlighted and move the legend below the panels."

Example helper flow:

```bash
python scripts/detect_figure_context.py /path/to/repo --description "workflow diagram for sample collection -> preprocessing -> integration -> modeling" --pretty

python scripts/make_schematic_figure.py \
  --repo /path/to/repo \
  --figure-id fig1-overview \
  --title "Study overview" \
  --description "sample collection -> preprocessing -> integration -> modeling" \
  --panel "Cohort design" \
  --panel "Molecular profiling" \
  --panel "Predictive model"
```

## Revision Examples

```bash
python scripts/update_figure_spec.py figures/specs/fig1-overview.json \
  --title "Updated study overview" \
  --set parameters.emphasis='\"Predictive model\"' \
  --add-output-format pdf

python scripts/export_figure_assets.py figures/specs/fig1-overview.json
```

## Boundary Examples

Stay in `quarto-manuscript`:

- "Export Figure 3 as SVG and PNG."
- "Change the panel labels from numbers to letters."
- "Organize the figure scripts and specs for this Quarto paper."

Hand back to the writing route in `quarto-manuscript`:

- "Rewrite the Discussion section."
- "Split `main.qmd` into section files."
- "Find citations for this claim."
