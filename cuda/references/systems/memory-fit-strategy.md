# Fit Strategy Order

## Default Order

1. delete avoidable buffers and duplicated representations
2. shorten intermediate lifetimes
3. checkpoint activations selectively
4. reduce batch size only as much as needed
5. recover throughput with gradient accumulation
6. move the sparse-to-dense boundary if dense expansion is too early
7. revisit optimizer-state cost if it still does not fit

## Throughput Rules

- prefer selective checkpointing over blind global checkpointing
- prefer changing the densification point over shrinking the whole workload when sparse stages are still dominant
- prefer accumulation over permanently tiny microbatches when arithmetic intensity collapses
- verify the post-fit throughput; a fitting job that starves the GPU is not a good result

## What To Hand Off To `cuda`

Once the job fits, pass along:

- new batch/microbatch configuration
- changed sparse-to-dense boundary
- any workspace limits
- any communication-buffer changes
