# Addendum: PTX Routing

Use this addendum only when the user explicitly asks for PTX, inline PTX, handwritten PTX, or PTX-level optimization guidance.

Do not load this file by default for ordinary V100 optimization work.

The purpose of this addendum is to answer:

- whether PTX is actually the right surface for this problem
- whether inline PTX is enough
- whether the guidance should stay portable or go deep on Volta `sm_70`
- whether sparse, irregular, or bioinformatics-heavy kernels justify PTX-level control

## Core Rule

PTX is a last-resort optimization tool.

Use it when:

- the hotspot is already proven
- the algorithm boundary is already reasonable
- library, fusion, binning, or layout changes are no longer the dominant lever
- a tiny low-level sequence or repeated hot primitive still needs tighter control

Do not use it when:

- the benchmark window is weak
- the real loss is PCIe, NVLink, staging, or HBM traffic
- the workload still wants a better sparse format, row binning policy, or kernel decomposition
- the problem maps cleanly to cuBLAS, cuBLASLt, cuSPARSE, CUB, or CUTLASS

## 1. Choose The Right Depth

Start with `references/ptx-general-guidelines.md` when:

- the user wants PTX guidance but not an architecture-specific deep dive
- the question is really about inline PTX, predicates, branch shaping, or control over a tiny sequence
- portability still matters

Route to `references/ptx-volta-extreme.md` when:

- the user explicitly wants the deepest Volta-specific PTX path
- the kernel is locked to Tesla V100 `sm_70`
- the problem depends on Volta control-flow, scheduler, or low-level instruction choices

Route to `references/ptx-sparse-bio-hotpaths.md` when:

- the explicit PTX request is about sparse hot paths
- the kernel is dominated by row skew, masks, filtering, compaction, irregular reductions, or gather/scatter glue
- the workload is bioinformatics-heavy and the hot path is not well served by standard library kernels

## 2. First Gate

Before writing PTX, answer these in order:

1. is the hotspot real and representative
2. is the problem still primarily algorithmic rather than instruction-level
3. would better fusion, specialization, binning, or compaction save more than PTX
4. is the target sequence small and stable enough to own safely

If any answer is unclear, go back to the higher-level path first.

## 3. What PTX Is Good For

PTX is most useful when you need tighter control over:

- predicate generation and conditional execution
- short branch-heavy inner sequences
- branchless select-style logic
- warp-level masks, ballots, compaction helpers, or irregular lane coordination
- tiny fixed micro-primitives that the compiler keeps materializing poorly
- sparse metadata handling where the arithmetic is cheap but the control flow is hot

PTX is usually not the right first answer for:

- large kernels with unresolved memory traffic issues
- dense math that already has strong library paths
- kernels whose performance is dominated by synchronization or staging
- problems where the right solution is to split or bin workloads rather than suppress branches

## 4. Inline PTX Versus Deeper PTX

Prefer inline PTX when:

- only a narrow sequence needs control
- the surrounding kernel should stay in CUDA C++
- you need one or two instructions the compiler does not shape well
- you want to keep the maintenance surface small

Escalate conceptually toward deeper PTX reasoning only when:

- the sequence is central and extremely hot
- the performance gain is benchmark-worthy
- portability costs are acceptable

## 5. Official References

Use these as the primary source base:

- PTX ISA: https://docs.nvidia.com/cuda/parallel-thread-execution/
- Inline PTX Assembly Application Note: https://docs.nvidia.com/cuda/inline-ptx-assembly/
- CUDA C++ Programming Guide: https://docs.nvidia.com/cuda/cuda-c-programming-guide/
- CUDA C++ Best Practices Guide: https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/
- Volta Tuning Guide: https://docs.nvidia.com/cuda/volta-tuning-guide/
- Handwritten PTX blog: https://developer.nvidia.com/blog/advanced-nvidia-cuda-kernel-optimization-techniques-handwritten-ptx/

## 6. Output Requirements

Be explicit about:

- whether PTX was explicitly requested
- why PTX is or is not the right surface for the problem
- whether the guidance stays portable or goes Volta-specific
- whether the hotspot is control-flow-limited, memory-limited, or layout-limited
- which follow-on reference should be loaded next
