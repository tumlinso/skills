# Bio Data Phases On V100

## Matrix Meanings

- single-cell RNA-seq: cells x genes, highly sparse, row-wise QC early, feature-wise stats later
- single-cell ATAC: cells x peaks, even sparser, binary or count-like values, heavy row skew
- velocity: paired spliced/unspliced matrices, often same sparsity structure family, more staging pressure
- dense embeddings: no longer a sparse-kernel problem; switch mental model to dense math and neighbor search

## Phase Meanings

### Row-Wise Phase

Typical operations:

- library size
- row normalization
- row filtering
- sparse x dense projection with per-row outputs

Implication:

- keep CSR as the master layout
- row sharding is natural
- row skew and `nnz/row` distribution matter

### Feature-Wise Phase

Typical operations:

- gene or peak sums
- feature means / variances
- repeated thresholding or regression-like passes

Implication:

- repeated CSR scans are usually the wrong answer
- build CSC or transpose once if feature-wise work is hot enough

### Sparse-To-Dense Boundary

Good reasons to go dense:

- projection reduces the problem enough that GEMM dominates
- downstream work is PCA, dense embeddings, or dense attention-like kernels
- irregular sparse glue is no longer the real bottleneck

Bad reasons to go dense:

- convenience
- avoiding a transpose decision
- forcing Tensor Core thinking on raw sparse counts

## Bio Workload Pathologies That Matter For Performance

- very skewed `nnz/row`
- many feature-wise passes hidden inside a mostly row-wise pipeline
- repeated filtering and remapping between sparse kernels
- over-conversion between sparse formats
- dense projection done too early, exploding memory traffic

## What To Carry Into `cuda`

When handing the task off to `cuda`, state:

- matrix meaning and axes
- dominant hot phase
- chosen layout
- expected sparse-to-dense boundary
- whether skew or format conversion is likely to dominate
