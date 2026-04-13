# Addendum: CPU-Centric To CUDA Porting

Use this addendum when the main problem is not yet "how do I tune this CUDA kernel?" but "how do I port this CPU-centric code efficiently to GPU on V100?"

This route is for code that still thinks like CPU code:

- cache-oriented loop nests
- thread-pool or task-queue structure
- pointer-heavy object graphs
- serial multi-stage pipelines
- callback-heavy branch logic
- sparse scientific code written for CPU locality instead of GPU throughput

## Core Rule

Do not port CPU-centric code literally to CUDA.

First decide:

- whether directive offload is good enough
- whether the problem wants a native CUDA rewrite
- whether the best answer is a mixed strategy

Then rewrite the work decomposition, data layout, and residency model before tuning low-level details.

## 1. First Gate

Ask these in order:

1. is the code regular enough that OpenMP target, OpenACC, or NVHPC may be acceptable
2. is the hot path dense or library-shaped enough that the real answer is explicit libraries
3. is the code sparse, irregular, or glue-heavy enough that native CUDA decomposition is the real endpoint
4. are the data structures or loop dependencies still shaped for CPU caches rather than GPU work distribution

If the answer to 3 or 4 is yes, do not start with micro-tuning.

## 2. CPU-Centric Red Flags

CPU-centric patterns that often port badly when copied literally:

- AoS or pointer-rich container graphs
- nested loops with serial dependencies
- work queues designed around CPU thread counts
- small virtual-call or callback-driven work units
- repeated host-visible staging between phases
- sparse traversals that mix layout, filtering, and arithmetic in one serial control flow

## 3. Route Choice

Read `references/cpu-porting-decision-tree.md` next to choose the endpoint:

- offload-first
- native CUDA rewrite
- mixed strategy

Read `references/cpu-to-cuda-rewrite-patterns.md` next when the endpoint is native CUDA or mixed.

Read `references/cpu-porting-sparse-bio.md` next when the workload is sparse, irregular, or bioinformatics-heavy.

## 4. Output Requirements

Be explicit about:

- what makes the current code CPU-centric
- whether offload or native CUDA is the right endpoint
- what decomposition change must happen before low-level tuning
- which follow-on reference should be loaded next
