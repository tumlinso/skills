# Crash Signature Map

Use this file when the summary names a crash signature and you need a fast interpretation.

## Common Signatures

- `Segmentation fault` or signal 11
  - likely host pointer, lifetime, or FFI boundary issue
  - next move: batch `cuda-gdb` if the first-pass summary is not already conclusive

- `an illegal memory access was encountered`
  - likely device out-of-bounds, stale pointer, or bad indexing
  - next move: `compute-sanitizer --tool memcheck`

- `device-side assert triggered`
  - likely kernel precondition failure or explicit assert
  - next move: rerun with assertions and debug symbols, then use `cuda-gdb` if the site is still unclear

- `invalid configuration argument`
  - likely bad launch geometry or dynamic shared-memory request
  - next move: inspect launch dimensions and shared-memory usage before deep debugging

- `unspecified launch failure`
  - usually a deferred kernel fault surfaced later
  - next move: `memcheck` first, then `cuda-gdb` if needed

- `warp out-of-range address`, `misaligned address`, `invalid __global__ read`
  - strong memory-fault evidence
  - next move: fix indexing and pointer math before profiling

- `Barrier error detected` or sync-check style wording
  - likely misuse of warp or block synchronization
  - next move: `synccheck`

- `Race reported` or shared-memory hazard wording
  - likely concurrent write or read-after-write bug
  - next move: `racecheck`
