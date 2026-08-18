# Native V100 SASS And PTX Triage

Use this route when the user explicitly asks for low-level dump work or when a
hot Volta kernel needs ptxas or SASS inspection after profiler triage.

Primary source:

- NVIDIA Volta Tuning Guide:
  https://docs.nvidia.com/cuda/volta-tuning-guide/

## Order

1. Keep PTX request-only.
2. Isolate the kernel first.
3. Read ptxas resource summary before raw SASS.
4. Read compact SASS behavior summaries before full dumps.

## Strong Scripts

- `scripts/architectures/volta/summarize_ptxas_verbose.py`
- `scripts/architectures/volta/summarize_sass_hotspot.py`
- `scripts/common/filter_objdump_sections.py`
- `scripts/dump_ptx_hotspot.sh`

## What To Look For

- registers and spill stores or loads
- HMMA or tensor instructions when the path should use Tensor Cores
- branch density and barrier density
- shared-memory versus global-memory instruction balance
- evidence that fusion widened the kernel beyond a sane inspection boundary

## Stop Early When

- ptxas already shows obvious spill pressure
- the kernel is still not isolated
- the real bottleneck is still topology, staging, or benchmark hygiene
