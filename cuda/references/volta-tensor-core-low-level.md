# Low-Level Volta Tensor Core Work

Use this reference only after `references/addendum-tensor-core-routing.md` has
established that the workload is genuinely Tensor Core-eligible and that
cuBLAS, cuBLASLt, or CUTLASS either still leave a stable gap or are forcing a
Volta custom op to stay split across too much library glue on Tesla V100 16 GB
`sm_70`.

This file is for the cases where you really should own the kernel.

For Volta custom ops, this is not just a last-resort rescue path. Use it once a
clean Tensor Core mapping exists and the value of the op is stable fused or
blocked Tensor Core ownership rather than generic library wrapping.

## Core Rule

Do not jump here because a dense kernel is slow.

Jump here only when:

- the benchmark window is representative
- the data path is already Tensor Core-friendly
- the library baseline is correct
- the remaining gap is stable enough to justify specialized kernel ownership

For explicit Volta custom-op requests, a stable gap can mean measurable launch,
epilogue, packing, or control overhead that survives even when the library
math path itself is correct.

## 1. Escalation Ladder

Use this order:

1. CUTLASS `Sm70` specialization
2. WMMA-based custom kernel
3. lower-level Volta MMA or inline PTX-style specialization only when the kernel is stable and benchmark-critical

If CUTLASS can express the tile shape and epilogue cleanly, prefer it over handwritten code.

On Volta custom-op work, do not stay library-backed so long that the extension
degenerates into a thin wrapper around repeated Tensor Core-capable library
calls with avoidable glue between them, but keep the library-backed option when
it already expresses the op cleanly.

## 2. When To Own The Kernel

Own the Tensor Core kernel when:

- the user explicitly wants a custom op and the op's value is stable Tensor
  Core tile ownership rather than generic wrapping
- the workload uses a fixed blocked layout that libraries do not model well
- the hot path is a fused tile kernel where matrix math and domain-specific glue are inseparable
- blocked sparse formats such as blocked ELLPACK produce stable dense subtiles that justify a dedicated path
- repeated layout conversion outside the kernel is dominating enough that a fused low-level kernel can remove it

Do not own the kernel when:

- the main problem is launch count
- the main problem is bytes moved
- the main problem is host-device staging
- the math tile is too irregular to keep a stable Tensor Core mapping

## 3. Tile And Fragment Rules For Volta

For `sm_70`:

- keep the tile structure stable across launches
- preserve Tensor Core-friendly dimensions at the blocked-tile boundary
- expect register pressure to be a first-class limiter
- use shared memory only when it reduces real global traffic or staging overhead

Low-level rules:

- keep fragment lifetimes short
- avoid overfusing long branchy regions around the MMA core
- benchmark multiple tile shapes rather than assuming the largest tile wins
- compare every shared-memory-heavy design against a lighter one

## 4. Blocked Formats And Sparse-To-Dense Tiles

Blocked sparse layouts can justify Tensor Core pursuit when:

- the nonzero structure is already expressed as fixed-size dense blocks
- the packing or blocking cost is amortized across enough tile math
- the end-to-end benchmark still wins after accounting for conversion and metadata handling

For blocked ELLPACK or similar formats:

- choose a block size that preserves stable dense tiles
- keep metadata compact and warp-friendly
- treat blocked ELLPACK-style storage as the default sparse Tensor Core candidate unless benchmark evidence clearly favors another blocked layout
- benchmark the blocked path against both the original sparse route and a dense-library baseline
- reject the blocked Tensor Core route if it only wins in isolated kernel timing while losing end-to-end

## 5. WMMA And Low-Level Kernel Mechanics

Use WMMA when:

- the tile math is regular
- the fused logic around the tile is lightweight enough to keep the MMA core fed
- CUTLASS does not give enough control

For Volta custom ops, WMMA is a normal ownership path once CUTLASS no longer
gives enough control over fusion, blocked layout, or epilogue structure. It is
not reserved only for pathological edge cases.

When hand-writing the kernel:

- keep loads, MMA, and epilogue structure explicit
- watch registers, local-memory traffic, and active warps together
- treat shared-memory carveout as a cost, not a free staging area
- compare against a split-kernel alternative if the fused epilogue grows branchy

If moving below WMMA:

- justify the drop with a measured gap, not curiosity
- keep the PTX or intrinsic surface narrow and isolated
- benchmark after every structural change, not only after the final polish

## 6. Benchmarking Rules

Benchmark low-level Tensor Core kernels fairly:

- compare against cuBLASLt and CUTLASS on the same representative shapes
- compare end-to-end runtime, not only kernel microbenchmarks
- separate one-time packing or conversion from the steady-state loop
- verify Tensor Core activity with Nsight Compute before claiming a low-level win

If the handwritten kernel wins only on a toy shape or one kernel launch, it is not ready to replace the library path.

## 7. Anti-Patterns

- owning a low-level Tensor Core kernel before establishing the library baseline
- converting cheap irregular glue into expensive dense work without end-to-end gain
- overfusing until register spills or occupancy collapse erase the Tensor Core benefit
- choosing a blocked format that improves one kernel while making transfers or metadata handling worse
- reading high board power as proof that the kernel is correct

## 8. Output Requirements

Be explicit about:

- why the library path is insufficient
- what tile or blocked structure justifies low-level ownership
- whether the route is CUTLASS, WMMA, or deeper specialization
- whether the custom-op requirement itself is the reason Volta should own the
  Tensor Core kernel earlier
- what the measured gain is versus the best library baseline
- whether the gain survives end-to-end benchmarking instead of only a microbenchmark
