# Counter Triage

Use this after `profile_ncu.sh` has already produced a valid `summary.txt`.

The point is to turn the summary's limiter into the next experiment quickly, not to stare at every metric the profiler exported.

## Common Patterns

### High DRAM, Weak SM

Interpret as:

- memory-bound
- or memory-serialization-limited

Try:

- fewer global passes
- better coalescing
- fused glue removal
- packed or vectorized loads when alignment allows
- inspect whether local-memory traffic is actually register spilling

### Weak Tensor Core Activity On Dense FP16 Work

Interpret as:

- shapes or math path are wrong for Volta dense compute

Try:

- cuBLAS or cuBLASLt baseline
- multiples-of-8 padding
- FP16 inputs with FP32 accumulation
- verify the library path before hand-tuning the custom kernel further

### Low Occupancy With High Registers

Interpret as:

- register pressure or over-fusion is limiting residency

Try:

- smaller tiles
- shorter live ranges
- register-cap experiments
- split obviously over-fused epilogues or long branchy regions
- compare local-memory traffic after each change, not just occupancy

### High Shared Memory Per Block

Interpret as:

- the occupancy tradeoff must be justified by real reuse

Try:

- compare with lighter shared-memory variants
- remove shared memory from warp-local subproblems
- inspect bank conflicts and wavefront growth

### Many Tiny Kernels With Good Individual Metrics

Interpret as:

- the end-to-end path is launch-bound even if each kernel looks healthy

Try:

- go back to Nsight Systems
- fuse first
- group library calls
- test CUDA Graph capture

### Scheduler Pain With Mixed Warp Progress

Interpret as:

- long divergent regions may be real
- or one general kernel is handling multiple stable workload classes badly

Try:

- short-row vs long-row specialization
- binning or compaction
- compare against a split-kernel path before polishing the current divergent kernel further

## Useful Nsight Compute Sections

For a first actionable pass, prefer:

- Roofline / Speed Of Light
- Memory Workload Analysis
- Occupancy
- Scheduler Statistics
- Launch Statistics

Use section-level evidence instead of overfitting to one metric name, because Nsight versions can change naming and availability.
