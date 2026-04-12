---
name: bio-experiments
description: Guardrails for scientifically correct handling of omics data, especially single-cell assays. Use when Codex is implementing preprocessing, QC, normalization, feature handling, metadata alignment, modality preparation, batch correction, dataset merging, harmonization, integration, or model-input construction for scRNA-seq, scATAC-seq, CITE-seq, spatial transcriptomics, or matched multimodal omics data.
---

# Bio Experiments

Use this skill to keep omics code scientifically correct when handling matrices, features, metadata, preprocessing state, and cross-dataset unification.

Keep this file small. Treat it as a router. Load only the assay branch and task branch that match the request.

Default to single-cell omics unless the user clearly asks for bulk workflows.

## Workflow

1. Classify the assay before proposing transformations.
   - scRNA-seq
   - scATAC-seq
   - CITE-seq
   - spatial transcriptomics
   - matched multimodal single-cell

2. Read exactly one assay reference first.
   - `references/assay-scrna.md`
   - `references/assay-scatac.md`
   - `references/assay-citeseq.md`
   - `references/assay-spatial.md`
   - `references/assay-multimodal.md`

3. Read `references/router-task-map.md`.
   - choose only the task branch that fits the request

4. Load `references/hard-constraints.md` whenever:
   - datasets are being merged or aligned
   - integration or harmonization is requested
   - normalization state is unclear
   - model-ready tensors or sparse matrices are being built

5. State assumptions before changing data semantics.
   - assay and modality
   - raw vs processed input state
   - matrix orientation
   - feature identifier namespace
   - sample, donor, batch, and study metadata available

## Reference Map

- `references/router-task-map.md`: route from assay selection into exactly one task branch
- `references/assay-scrna.md`: RNA counts, feature semantics, QC order, normalization state, and pseudobulk boundaries
- `references/assay-scatac.md`: peak and fragment semantics, peak-set compatibility, sparsity-aware preprocessing, and gene-activity cautions
- `references/assay-citeseq.md`: RNA plus ADT handling, antibody-derived tag caveats, and modality alignment
- `references/assay-spatial.md`: spot or cell-level spatial data, coordinate semantics, image linkage, and spatially aware QC
- `references/assay-multimodal.md`: matched multi-assay objects, paired-cell assumptions, and missing-modality handling
- `references/task-preprocessing.md`: preprocessing order, assay-conditional steps, and processing-state checkpoints
- `references/task-dataset-unification.md`: identifier alignment, schema harmonization, feature-space checks, and merge policies
- `references/task-integration.md`: aggressive harmonization defaults, method choice, and over-correction warnings
- `references/task-model-inputs.md`: tensor construction, sparse-to-dense boundaries, split hygiene, and leakage checks
- `references/hard-constraints.md`: non-negotiable scientific correctness rules

## Common Sequences

- assay reference -> `references/task-preprocessing.md`: implement a preprocessing pipeline for one assay correctly
- assay reference -> `references/task-dataset-unification.md` -> `references/hard-constraints.md`: merge or align studies without mixing incompatible data
- assay reference -> `references/task-integration.md` -> `references/hard-constraints.md`: harmonize datasets aggressively while stating distortion risks
- assay reference -> `references/task-model-inputs.md` -> `references/hard-constraints.md`: build tensors or sparse matrices with correct semantics and no leakage

## Output Requirements

Be explicit about:

- assay and modality
- expected raw input type and current processing state
- matrix orientation and feature semantics
- metadata columns required before merge or integration
- which task reference informed the recommendation
- what compatibility checks must pass before combining data
- what biological signal could be distorted by the proposed transformation

Hard constraints:

- Do not merge datasets before checking feature-space compatibility and processing state.
- Do not normalize counts twice or apply log transforms without confirming the current state.
- Do not treat peaks, genes, proteins, spots, and cells as interchangeable feature types.
- Do not run batch correction before assay-specific QC and filtering.
- Do not silently collapse batch, donor, study, chemistry, or modality differences.
- Do not create train or validation matrices that leak donor, study, or cell information across splits.
