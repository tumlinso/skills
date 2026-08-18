# Native V100 Register Pressure And Occupancy

Use this route when Volta tuning is blocked by spills, low occupancy, or launch
bounds questions.

Primary sources:

- NVIDIA Volta Tuning Guide:
  https://docs.nvidia.com/cuda/volta-tuning-guide/
- CUDA Best Practices Guide:
  https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/

## What Volta Changes

Volta lowers core FMA dependency latency and improves L1/shared behavior enough
that the best point on the occupancy-versus-ILP curve should be re-evaluated.
Do not cargo-cult Pascal-era occupancy targets.

## Triage Order

1. Read ptxas verbose output first.
2. Check whether spills or shared-memory carveout are the real occupancy limiter.
3. Only then decide whether to reduce registers, lower tile size, or specialize.

## Prefer Lower Registers When

- spills create clear local-memory traffic
- occupancy is too low to hide memory or control latency
- a small source rewrite removes live-range overlap cleanly

## Prefer Higher Registers When

- the kernel stays spill-free
- ILP is paying for itself
- occupancy is already sufficient for the observed latency class

## Strong Tools

- `scripts/architectures/volta/summarize_ptxas_verbose.py`
- `scripts/architectures/volta/summarize_sass_hotspot.py`
- `scripts/profile_ncu.sh`

## Do Not

- optimize for occupancy alone
- reduce registers by forcing a decomposition that adds extra HBM passes
- read raw SASS first when ptxas already shows the limiter
