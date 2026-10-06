# CUDA Diagnostics Workflow

Use this reference when the first question is how to inspect or stabilize CUDA
behavior without flooding context with raw output.

## Order Of Operations

1. Prove the workload is representative.
2. Use Nsight Systems for starvation, overlap, loader, or topology trouble.
3. Use Nsight Compute for one hot kernel once the timeline window is stable.
4. Use `compute-sanitizer` before `cuda-gdb` for memory, race, or sync trouble.
5. Use focused PTX, SASS, or objdump only after the hot path is isolated.

## Script Surface

- `scripts/profile_nsys.sh`
- `scripts/profile_ncu.sh`
- `scripts/debug_crash.sh`
- `scripts/debug_compute_sanitizer.sh`
- `scripts/debug_cuda_gdb.sh`
- `scripts/dump_ptx_hotspot.sh`
- `scripts/common/filter_objdump_sections.py`
- `scripts/common/summarize_cuda_diagnostics.py`
- `scripts/architectures/volta/summarize_ptxas_verbose.py`
- `scripts/architectures/volta/summarize_sass_hotspot.py`

## Summary-First Rule

Prefer these compact artifacts:

- benchmark summary JSON or text
- Nsight Systems stall summary
- Nsight Compute limiter summary
- compact crash signature summary
- focused symbol dump summary
- compact ptxas resource summary
- compact SASS behavior summary

Inspect raw logs only when the summaries disagree or omit the root cause.

## Build Discipline During Diagnostics

- Build only the target architecture unless portability is the actual question.
- Keep one hot kernel per TU when low-level inspection is likely.
- Do not compare kernels built from materially different binary matrices unless
  the test is explicitly about portability cost.
