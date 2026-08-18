# Code Organization For Low-Level CUDA Work

Use this reference when the task includes generated CUDA/C++ code, hot-kernel
inspection, or repeated compile-profile-dump loops.

## Core Layout Rules

1. Keep one hot kernel per translation unit when deep profiling, PTX, SASS, or
   objdump inspection is likely.
2. Keep reusable micro-primitives in narrow headers close to the kernel that
   owns them.
3. Prefer architecture-specific builds over one wide build during tuning.
4. Stay away from unnecessary standard-library surfaces in hot code.
5. Use comments only to direct deeper reading or record behavior-sensitive
   constraints.

## Comment Style

Use short imperative comments like:

- `read tile_iter.h for lane-to-fragment contract`
- `keep this branch uniform at warp scope`
- `stage stays in shared to avoid second HBM read`
- `split here only if reg spill exceeds target`

Do not add explanatory prose for obvious statements.

## When To Fuse

Bias toward aggressive fusion on the native Volta path when:

- the passes share the same sparse or glue-heavy working set
- the alternative adds extra HBM round-trips
- launch overhead is material relative to the work
- intermediate state is cheap enough to keep in registers or shared memory

Split instead when:

- registers spill hard enough to collapse occupancy
- one stage wants a library path and the rest does not
- synchronization boundaries are already forced by NCCL, device-host staging, or
  persistent producer-consumer queues
- the architecture wants a different staging model, such as Ampere async copy or
  Hopper TMA

## Dump Hygiene

- Run `scripts/common/check_single_kernel_tu.py` before dumping.
- Use `scripts/split_cuda_translation_unit.py` if a TU is still too wide.
- Compile only the target architecture under study.
- Filter objdump or disassembly output down to the symbol and decision class you
  care about before loading it into context.
- For Volta-native deep work, pair `scripts/architectures/volta/emit_profile_build.py`
  with `scripts/architectures/volta/summarize_ptxas_verbose.py` and
  `scripts/architectures/volta/summarize_sass_hotspot.py` so the skill can read
  compact register, spill, branch, and memory summaries instead of raw dumps.

## Required Dense Notes

For behavior-sensitive code, document:

- memory residency of critical intermediates
- expected branch structure and whether it is intentionally divergent
- expected launch granularity
- any known performance incursions accepted for correctness or portability

If the code is meant for agent reuse, prefer many narrow files with directed
comments over one large file with prose.
