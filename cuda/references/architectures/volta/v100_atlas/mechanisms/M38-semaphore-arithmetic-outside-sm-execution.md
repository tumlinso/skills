# M38 — Semaphore arithmetic outside SM execution

> A completion word can be updated without a shader or payload transfer.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** DMA, semaphores, non-SM, coordination.
**Prerequisites:** R09 R06. **Evidence:** S12 S15.

## Established substrate [D; reachability K; public alternatives C]

Pinned Volta UVM code emits release, increment and timestamp commands with DATA_TRANSFER_TYPE_NONE. This is actual driver usage, not merely an enticing field. Reduction affects the completion word rather than an array.

## Appropriation hypothesis

Express phase completion or bounded event counting as command-engine work. A pipeline may publish progress without a tiny kernel or resident polling warp. A command timestamp can mark a different execution boundary from a shader clock.

## Cost and rejection boundary

Ordering, flushes, target permissions, counter wrap and queue ownership remain necessary. The private helper is not an ordinary callable CUDA API. Do not infer a free general ALU or shared time base across GPUs.

## Next reads

Compositions: C27 C28. Experiments: E28 E22.
