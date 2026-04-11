# Real-Data Benchmarking

Use this reference when benchmarking with real biological data or when deciding how synthetic and real cases should coexist.

The main rule is:

- synthetic benchmarks are for controlled stress and differential diagnosis
- real-data benchmarks are for representativeness

Both are required.

## Real-Data Contract

A `real` benchmark run should point to a repo-local dataset manifest rather than relying on undocumented paths or ad hoc flags.

Required manifest fields:

- `dataset_id`
- `dataset_kind`
- `path` or `paths`
- `format`
- `rows`
- `cols`
- `nnz` when available
- semantic tags such as `scrna`, `scatac`, `multimodal`, `quantized`, `training`, or `inference`

Recommended fields:

- shard layout
- batch or donor grouping
- row-nnz percentiles
- feature-order notes
- slice policy when the full dataset is too large for every benchmark run

## Preserve Real Semantics

Do not normalize away the properties that create the actual bottleneck.

Examples:

- keep real row-skew if row-skew drives warp imbalance
- keep real feature popularity skew if it changes cache or reuse behavior
- keep real shard imbalance if it changes multi-GPU placement or reduction cost
- keep real mitochondrial flags or gene-group annotations if preprocess filters depend on them

Only add a separate normalized replay mode when you explicitly want a cleaner microbenchmark.

## Tier Relationship

Use all three tiers together:

- `small`: quick correctness and smoke runs
- `large`: synthetic stress tuned to this machine
- `real`: representative production-like evidence

When they disagree:

- trust `real` for representativeness
- trust `large` for controlled bottleneck isolation
- trust `small` only for smoke and local iteration

## Real-Data Summary Requirements

A real-data summary should always state:

- the dataset id or manifest
- whether the full dataset or a slice was used
- the scale actually reaching the timed loop
- whether preprocessing or format conversion changed the data before timing
- whether the run remained on-device after loading

## Output Requirements

Be explicit about:

- what is real vs synthetic
- what semantic properties of the data are likely driving the result
- whether the benchmark still reflects the actual use case after any slicing or preprocessing
