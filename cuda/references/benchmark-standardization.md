# Benchmark Standardization

Use this reference when the task is to standardize benchmark targets, profiler interop, or benchmark summaries across V100 repos.

The rule is simple:

- benchmark binaries emit raw structured measurements
- helper scripts emit the concise summaries and interpretations
- the skill reads the summaries first and raw artifacts only when needed

## Required Benchmark Run Artifacts

Every benchmark run should write one run directory containing:

- `run_config.json`
- `results.json`
- `summary.json`
- `summary.txt`

If profiled, the same run family should also produce:

- `nsys/summary.json`
- `nsys/summary.txt`
- `ncu/summary.json`
- `ncu/summary.txt`
- `combined_summary.json`
- `combined_summary.txt`

Do not make the skill parse raw benchmark stdout when a compact summary can answer the question.

## Required CLI Contract

Every benchmark target that wants easy interoperability should support:

- `--dataset-tier small|large-compute|large-transfer|real`
- `--dataset-manifest PATH` for `real`
- `--warmup N`
- `--repeats N`
- `--output-dir PATH`
- `--output-json PATH` or a fixed output-dir convention
- `--profile-friendly`

Repo-local flags are fine, but these baseline flags should exist and retain the same meaning across targets.

Benchmark-producing runs must also be serialized on shared hosts. The skill-owned
profiler wrappers already do this. Raw benchmark commands should run through
`scripts/with_benchmark_mutex.sh` or embed an equivalent host-global lock keyed
by `CUDA_V100_BENCHMARK_MUTEX_PATH`.

If a repo still accepts plain `large`, treat it as a compatibility alias only. The supported contract should name `large-compute` and `large-transfer` explicitly.

## Summary-First Principle

Make the scripts do most of the repetitive interpretation work.

### Benchmark binary responsibilities

- emit exact configuration and scale information
- separate warmup from measured iterations
- emit stable phase names
- emit correctness or checksum status separately from timings
- emit raw phase timings and counters

### Script responsibilities

- reduce raw benchmark output to compact benchmark verdicts
- reduce Nsight outputs to compact profiler verdicts
- merge benchmark plus profiler evidence into one short combined interpretation

### Skill responsibilities

- read `combined_summary.txt` first when it exists
- otherwise read `summary.txt`
- only load raw logs, CSV, or report artifacts if the summaries disagree or remain inconclusive

## Required Phase Names

Use stable phase names whenever they apply:

- `load_or_generate`
- `pin_or_stage`
- `h2d`
- `steady_state_compute`
- `collective_or_reduce`
- `d2h_or_materialize`
- `end_to_end`

Use stable NVTX labels that match these phase names or a clearly documented refinement of them.

## Required JSON Shape

`run_config.json` should minimally include:

```json
{
  "benchmark_id": "scrna-preprocess",
  "workload_family": "scrna",
  "dataset_tier": "large-compute",
  "scenario_kind": "large-compute",
  "dataset_id": "synthetic-pareto-v1",
  "dataset_manifest": null,
  "visible_device_ids": [0, 1, 2, 3],
  "topology": "v100-4gpu-diagonal-nvlink",
  "warmup": 1,
  "repeats": 4,
  "profile_friendly": true
}
```

`results.json` should minimally include:

```json
{
  "phases": [
    {
      "name": "steady_state_compute",
      "steady_state": true,
      "warmup_iterations": 1,
      "measured_iterations": 4,
      "wall_ms": 28.752,
      "metrics": {
        "approx_nnz_per_s": 149400000000.0
      },
      "counters": {
        "nnz": 1073741824
      }
    }
  ],
  "metrics": {
    "approx_nnz_per_s": 149400000000.0
  },
  "checks": {
    "valid": true
  }
}
```

## Representativeness Rules On This Machine

Treat a run as representative only when:

- warmup/setup noise is outside the measured steady-state phase
- the benchmark records enough repeated steady-state iterations
- the benchmark records device placement on this 4x V100 host
- multi-GPU runs preserve the real fast pairs `0<->2` and `1<->3`
- `large-compute` runs are large enough to create repeated hot kernels
- `large-transfer` runs are large enough to create visible transfer or collective behavior
- `real` runs still reflect the semantic properties that matter in production

## Required Data Tiers

Every important benchmark should support:

- `small`: smoke or development loop
- `large-compute`: synthetic or replayed stress case sized to expose the compute ceiling on this host
- `large-transfer`: synthetic or replayed stress case sized to expose transfer, staging, or collective limits on this host
- `real`: repo-local real dataset or real-data slice described by a manifest

Do not treat `small` as proof of end-to-end throughput.

Do not collapse `large-compute` and `large-transfer` into one ambiguous `large` label in new benchmark contracts.

## Script Workflow

Use these scripts in order:

1. run the benchmark under `scripts/with_benchmark_mutex.sh -- benchmark_target ...` unless the target already embeds an equivalent mutex
2. benchmark target writes `run_config.json` and `results.json`
3. `scripts/summarize_benchmark_run.py` writes `summary.json` and `summary.txt`
4. `scripts/profile_nsys.sh --benchmark-summary ...` writes Nsight summaries and a combined summary
5. `scripts/profile_ncu.sh --benchmark-summary ...` writes Nsight summaries and a combined summary
6. `scripts/combine_benchmark_summaries.py` merges benchmark, timeline, and kernel summaries when a fully merged interpretation is needed

## Output Requirements

Be explicit about:

- whether the result is `small`, `large-compute`, `large-transfer`, or `real`
- whether the summary records `scenario_kind`
- whether the timed phase is truly steady state
- whether the measured window is compute-dominant, transfer-dominant, or mixed
- what phase dominated wall time
- what bottleneck dominated after combining benchmark and profiler evidence
- what next measurement or optimization step should happen
