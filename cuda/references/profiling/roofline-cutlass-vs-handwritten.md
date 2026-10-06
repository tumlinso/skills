# CUTLASS Vs Handwritten Dense Kernels

## Prefer cuBLASLt First

If the path is still recognizable as GEMM plus a modest epilogue, benchmark cuBLASLt before both CUTLASS and handwritten kernels.

## Prefer CUTLASS When

- the operation is still tiled matrix math
- you need more control than cuBLASLt exposes
- the kernel shape is stable enough to justify specialization
- the main gain comes from tile or epilogue control, not domain-specific irregular logic

## Prefer Handwritten Kernels When

- domain-specific fused logic is the real reason to own the kernel
- irregular indexing or sparse glue dominates
- the math core is only part of a larger fused pass
- the library or CUTLASS path would force too many extra HBM passes

## Practical Rule On V100

For dense Volta math:

- cuBLASLt is the default baseline
- CUTLASS is the next option when you still want a matrix-math kernel
- handwritten WMMA is the ownership path after CUTLASS when Volta custom-op
  fusion, blocked layout control, or repeated library glue justify owning the
  kernel earlier

## Decision Checklist

- does the hot path still look like GEMM?
- is the missing performance due to layout/epilogue control?
- would a custom kernel remove full-memory passes that libraries cannot?
- is this explicitly a Volta custom op where stable Tensor Core ownership is
  the product requirement rather than an afterthought?
- is the cost of owning a handwritten kernel justified by repeated use and measurable gain?
