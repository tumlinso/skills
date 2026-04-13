# Common Blockers

Use this reference when the candidate region is not obviously clean.

## Aliasing And Ownership

- pointers or references may overlap
- ownership is spread across helpers
- one call path mutates state that another path assumes is read-only

These problems usually push a region into `possible with restructuring` or `poor OpenACC target`.

## Hidden Temporaries

- compiler-visible temporaries are not obvious in the source
- helper routines allocate scratch space internally
- per-call staging buffers defeat residency plans

## Allocation Churn

- allocate or free inside hot loops
- resize scratch buffers repeatedly
- rebuild metadata every iteration

Fix the lifetime first. Directive clauses do not repair allocator churn.

## Indirect Access And Gather/Scatter

- lookup tables drive memory access
- adjacency lists or sparse structures dominate indexing
- writes scatter into shared state

These patterns are not automatic rejections, but they demand an honest data-movement and dependency analysis.

## Scans And Dependencies

- prefix sums
- wavefront updates
- recurrences
- loop-carried state mutation

Do not label these as reductions. They normally require decomposition changes before offload.

## Tiny Or Transfer-Dominated Regions

- very small trip counts
- arithmetic too light to pay for transfers
- kernels surrounded by host-only setup and teardown

Hot does not mean offload-worthy. The transfer bill still matters.

## CPU-Centric Layouts

- loop orders optimized for host caches
- struct-heavy layouts that frustrate device access
- decomposition boundaries chosen for CPU threads rather than residency

Sometimes the right answer is a small data-layout cleanup. Sometimes the right answer is to reject the port.
