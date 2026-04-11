# Examples

## Discovery Only

Prompt:

`Use $public-omics-intake to find public single-cell RNA-seq datasets for adult human liver fibrosis and rank the best integration candidates.`

Expected behavior:

- infer a structured query spec
- search GEO and or SRA metadata
- rank candidates with integratability scores
- return assumptions and candidate list
- do not create directories or download files yet

## Root Prompt

If the user has not provided a destination, stop and ask:

`Where should the dataset root live?`

Ask that once before any directory creation, manifest writing, symlink creation, or download action.

## Processed-First Acquisition

Prompt:

`Use $public-omics-intake to fetch processed public files for GSE171555 into /data/public-omics for my liver-fibrosis-atlas project.`

Expected behavior:

- plan the canonical layout under `/data/public-omics`
- write machine-readable manifests and provenance
- fetch GEO metadata plus matrix and supplementary files
- skip raw SRA acquisition

## Metadata-Only SRA Intake

Prompt:

`Use $public-omics-intake to capture metadata only for mouse developmental heart SRA studies under /data/public-omics.`

Expected behavior:

- write study and run metadata manifests
- do not call `prefetch`
- keep raw download paths only in the plan

## Explicit Raw Request

Prompt:

`Use $public-omics-intake to fetch raw SRA runs for PRJNA720779 under /data/public-omics and record the provenance.`

Expected behavior:

- confirm the request is explicit raw scope
- capture run metadata
- use SRA Toolkit for raw acquisition
- do not perform downstream alignment or quantification
