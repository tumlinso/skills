# V100 Profiling And Interpretation

Use this reference when the task is not just "run a profiler," but **decide quickly whether a V100 measurement is trustworthy and what to do next**.

If the binary still segfaults, trips a device assert, or dies before a representative run window exists, do not start here. Route first into `references/addendum-crash-debugging.md`.

The profiling wrappers are now designed to emit **minimal decision-ready summaries**:

- `scripts/profile_nsys.sh` writes `summary.txt` and `summary.json` that answer:
  - did CUDA trace data export correctly?
  - is this run representative of steady-state timing, or mostly setup / transfers / allocator churn?
  - what is the next rerun or tuning action?
- `scripts/profile_ncu.sh` writes `summary.txt` and `summary.json` that answer:
  - are the counters usable?
  - what limiter is most likely on V100?
  - do we have enough repeated hot-kernel samples to trust the diagnosis?
  - by default it uses a compact V100 metric list instead of a huge full-set replay

Both wrappers capture noisy command and profiler output into files inside the run directory and print the summary path plus a short human-readable verdict. When you already have a benchmark `summary.json`, pass it with `--benchmark-summary` so the wrapper also emits a `combined_summary.txt` and `combined_summary.json` instead of forcing the skill to merge raw artifacts in-context.

## Quick Map

- `Recommended Workflow`
- `Decision Rules`
- `How To Read Nsight Systems On V100`
- `How To Read Nsight Compute On V100`
- `When To Rerun`
- `What "Better" Looks Like On V100`

## Recommended Workflow

1. Run the benchmark normally first.
   - Use the benchmark or test output for throughput numbers.
   - Do not use Nsight Compute runtime as your throughput measurement. Replay changes runtime.
   - If the binary still crashes, use the crash-debugging route before this workflow.

2. Run `profile_nsys.sh` first.
   - Nsight Systems decides whether the benchmark run reflects steady-state behavior or mostly setup.
   - Trust its `summary.txt` to tell you whether allocator churn, memcpy traffic, or tiny-kernel trains are distorting the run.

3. Only if the timeline is usable, run `profile_ncu.sh` on the hot path.
   - Nsight Compute decides why the hot kernel behaves that way.
   - Trust its `summary.txt` for limiter classification, not throughput.

4. Compare against the fastest plausible alternative.
   - GEMM-like work: compare against cuBLAS or cuBLASLt.
   - sparse primitive-shaped work: compare against cuSPARSE or CUB-based preprocessing baselines.
   - glue-heavy work: compare against fused custom kernels or CUDA Graph capture, not just against the current fragmented implementation.

## Decision Rules

### A good Nsight Systems run

Treat the timeline as representative when:

- CUDA kernel tables exported successfully
- the summary says `status: ok`
- setup costs like `cudaMalloc` / `cudaFree` are not dominating the measured interval
- steady-state transfer traffic is not dominating the measured interval
- the hot kernels have enough repeated instances to look like a real steady-state sample

### A good Nsight Compute run

Treat the counters as representative when:

- the summary says `counter_valid: yes`
- the hot kernel has enough repeated samples for the question you are asking
- the kernel you profiled is actually the hot kernel from the paired Nsight Systems run

Do **not** treat Nsight Compute runtime as representative throughput timing, even when the counters are valid.

## How To Read Nsight Systems On V100

Nsight Systems answers: **does this run reflect real end-to-end behavior, and where is time going?**

### If `summary.txt` says allocator churn dominates

Interpretation:

- the run is measuring setup more than steady-state compute
- benchmark throughput may still be fine, but the timeline is not a clean steady-state sample

What to do:

- pre-allocate buffers
- move warmup and one-time setup out of the measured loop
- rerun the timeline on the steady-state phase

### If memcpy activity is prominent

Interpretation:

- PCIe or host-device staging is stealing the run
- data residency is weak or transfers are fragmented

What to do:

- keep tensors resident on device
- use pinned host memory for unavoidable transfers
- batch copies
- rerun after removing steady-state host bounce

### If there are many very short kernels

Interpretation:

- launch overhead may dominate end-to-end behavior

What to do:

- fuse pointwise passes
- batch small work
- test CUDA Graph capture on the steady-state loop

## How To Read Nsight Compute On V100

Nsight Compute answers: **why is this hot kernel behaving that way?**

### If the summary says memory-bound

Interpretation:

- the kernel is limited more by bytes moved than by arithmetic throughput

What to do:

- improve coalescing
- reduce extra global-memory passes
- fuse memory-bound glue
- prefer vectorized packed loads/stores when alignment allows

### If the summary says compute-path mismatch

Interpretation:

- the math path is wrong for Volta dense work
- Tensor Cores may not be firing when they should

What to do:

- benchmark cuBLAS or cuBLASLt first
- verify FP16 input plus FP32 accumulation where numerically acceptable
- align important dimensions to multiples of 8

### If the summary says register-limited

Interpretation:

- register pressure is limiting residency

What to do:

- benchmark smaller tiles
- shorten live ranges
- test a register-cap experiment

### If the summary says shared-memory-limited

Interpretation:

- shared memory usage may be buying reuse at too high an occupancy cost

What to do:

- confirm the reuse is worth it
- compare against a lighter shared-memory design
- check bank conflicts before increasing carveout further

## When To Rerun

Rerun Nsight Systems when:

- the summary says `status: rerun`
- CUDA trace export failed
- allocator churn or transfer traffic dominates but the question is steady-state throughput
- there are too few repeated kernel instances to trust the sample

Rerun Nsight Compute when:

- the summary says `counter_valid: no`
- you profiled the wrong kernel
- you only have one or two hot-kernel samples and need stronger evidence
- you need deeper counters after a quick `detailed` pass, in which case rerun with a heavier set or extra sections
- you need deeper counters after the default compact metric pass, in which case rerun with `--set full` or extra sections

## What "Better" Looks Like On V100

- Nsight Systems says the measured interval is mostly steady-state GPU work, not setup
- fewer host-device transfers appear in the steady-state timeline
- allocator churn is outside the hot path
- hot dense kernels show stronger Tensor Core use
- memory-bound kernels move fewer bytes per unit of useful work
- sparse workloads improve by layout, packing, or row-binning decisions rather than fake occupancy wins
