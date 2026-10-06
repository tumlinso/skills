# Pipeline Bottlenecks

## Common Host-Side Failure Modes

- parsing or preprocessing takes longer than the GPU step
- sparse batch assembly is serialized or heavily fragmented
- pinned memory is not used for real transfers
- copies are too small and too frequent
- setup work leaks into steady-state timing
- synchronization points erase intended overlap

## Classification

### Loader Bound

Symptoms:

- GPU idle gaps before step launch
- worker threads saturated

Actions:

- increase loader concurrency only when the storage path can support it
- simplify per-sample work
- move repeated transforms out of the per-step path

### Batch Assembly Bound

Symptoms:

- sparse index/value packing dominates host time
- variable-size batches produce jitter

Actions:

- reduce fragmentation
- precompute reusable index maps
- benchmark moving part of assembly or follow-on transforms onto the GPU

### Transfer Bound

Symptoms:

- memcpy lanes dominate the timeline
- many small copies

Actions:

- pin memory
- batch transfers
- reduce intermediate host-visible stages

### Overlap Failure

Symptoms:

- compute and transfer should overlap but do not

Actions:

- check stream usage and synchronization points
- isolate setup from steady state
- simplify the pipeline until overlap behavior is obvious
