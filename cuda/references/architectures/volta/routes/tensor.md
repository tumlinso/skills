# Volta Tensor Route

Use for Tensor Core eligibility, Tensor Core routing, dense blocked custom-op ownership, or weak Tensor activity on V100.

Rules:

1. Check Tensor Core eligibility before owning a regular FP kernel.
2. Keep the library path available when it already expresses the op cleanly.
3. On Volta custom-op work, escalate earlier to CUTLASS or WMMA when fusion, blocked layout ownership, or HBM-pass removal is the real win.
4. Do not load low-level ownership docs until the Tensor path is clearly the right path.

Load order:

1. `references/addendum-tensor-core-routing.md`
2. `references/architectures/volta/routes/torch-op.md` only if the boundary is really a PyTorch custom op
3. `references/volta-tensor-core-low-level.md` only when the library or CUTLASS path is correct and still too slow or too glue-heavy
