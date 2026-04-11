# Benchmark Target Authoring

Use this reference when writing a new benchmark build target that should interoperate cleanly with the `cuda-v100` scripts and summaries.

## Core Rule

Write the benchmark so the scripts can summarize it without custom parsing.

That means:

- stable CLI flags
- structured output files
- stable phase names
- stable NVTX labels
- correctness separated from timing

## Build Target Expectations

Create a normal repo build target for the benchmark.

Do not keep important benchmark binaries as `/tmp`-only throwaways if they are part of the supported benchmarking surface.

The target should:

- build through the repo's normal build system
- accept the common benchmark CLI contract
- emit the standard run directory artifacts
- be callable directly from `profile_nsys.sh` and `profile_ncu.sh`

## Required CLI Flags

Support these flags with the standard meaning:

- `--dataset-tier small|large|real`
- `--dataset-manifest PATH`
- `--warmup N`
- `--repeats N`
- `--output-dir PATH`
- `--output-json PATH`
- `--profile-friendly`

Additional workload-specific flags are fine.

## Required Output Files

Write:

- `run_config.json`
- `results.json`

Then either:

- call `scripts/summarize_benchmark_run.py`, or
- emit the same `summary.json` and `summary.txt` shape yourself

Prefer reusing the shared summarizer unless the benchmark genuinely has extra logic worth preserving.

## Required Timing Structure

1. Parse config.
2. Prepare inputs or load dataset.
3. Do warmup.
4. Time only measured iterations.
5. Emit correctness/checksum separately.
6. Write structured results.

Do not mix one-time setup, allocation churn, or logging-heavy code into the measured steady-state phase unless the benchmark is explicitly about those costs.

## Required NVTX Structure

Wrap the measured regions with stable labels.

Use these names when they apply:

- `load_or_generate`
- `pin_or_stage`
- `h2d`
- `steady_state_compute`
- `collective_or_reduce`
- `d2h_or_materialize`
- `end_to_end`

If you need a more specific name, keep it clearly nested under one of those meanings.

## Single-GPU Template

Use this pattern for kernel or local pipeline benchmarks:

1. load or synthesize the case
2. allocate and upload once
3. warm the kernel or pipeline
4. time `steady_state_compute`
5. emit throughput and scale counters
6. run correctness checks outside timed scope

## Multi-GPU Template

Use this pattern for upload, sharding, or reduction-heavy workloads:

1. load or synthesize inputs
2. record visible devices and placement assumptions
3. warm stage/upload or reduction structures
4. time upload, compute, and reduction as separate phases
5. emit placement plus data-volume counters
6. emit final correctness or checksum outside timed scope when possible

## Interop With The Shared Scripts

Design the benchmark so these commands work without custom glue:

```bash
benchmark_target --output-dir /tmp/run --dataset-tier large --warmup 1 --repeats 4
python3 scripts/summarize_benchmark_run.py /tmp/run
bash scripts/profile_nsys.sh --benchmark-summary /tmp/run/summary.json -- benchmark_target ...
bash scripts/profile_ncu.sh --benchmark-summary /tmp/run/summary.json -- benchmark_target ...
```

## Templates

Use these asset templates as a starting point:

- `assets/benchmark_run_config.template.json`
- `assets/benchmark_results.template.json`
- `assets/benchmark_manifest.template.json`
- `assets/dataset_manifest.template.json`

## Output Requirements

Be explicit about:

- which phase is the real steady-state phase
- which counters explain the throughput number
- which dataset tier is being exercised
- whether the target is suitable for `nsys`, `ncu`, or both
