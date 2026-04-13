# CPU-To-CUDA Porting Decision Tree

Use this file after `references/addendum-cpu-porting.md`.

The point is to choose the right endpoint before spending time porting the wrong surface.

## 1. Offload Is Acceptable When

OpenMP target, OpenACC, or NVHPC may be acceptable when:

- the loop nest is regular
- the data layout is already simple enough
- the hot path is not sparse, branch-heavy, or gather/scatter-heavy
- hidden movement can be measured and kept under control
- developer speed matters more than absolute peak control

If this is the case, continue into the NVHPC references before writing native CUDA.

## 2. Native CUDA Is The Default When

Prefer native CUDA/C++ plus explicit libraries when:

- sparse format control matters
- the work is irregular or glue-heavy
- explicit data residency matters
- fusion, binning, or specialization will decide performance
- the hot path needs cuBLAS, cuSPARSE, CUB, NCCL, or custom kernels explicitly

If this is the case, continue into `references/cpu-to-cuda-rewrite-patterns.md`.

## 3. Mixed Strategy Is Often Best When

Use a mixed strategy when:

- non-critical regular loops can stay on an offload surface
- the hot path still needs explicit CUDA or library calls
- engineering speed matters, but not enough to hide the hot path behind an abstraction

Typical mixed answer:

- offload or standard C++ for cold or regular code
- explicit CUDA/C++ and libraries for the hot path

## 4. Dense, Sparse, And Library Boundaries

Choose explicit libraries first when:

- the ported path is actually GEMM, batched GEMM, SpMM, SpMV, reductions, scans, or sorts in disguise

Do not write custom kernels because the CPU code looked bespoke.

Change the boundary first. Then compare against the best explicit library path.

## 5. Anti-Patterns

- forcing directive offload onto sparse irregular hot paths
- rewriting native CUDA for a regular loop that is not performance-critical
- treating “it compiles on GPU” as proof that the right endpoint was chosen
- preserving a CPU decomposition that prevents explicit library use
