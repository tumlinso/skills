# Running the V100 benchmark campaign

The runner uses the CUDA 12.9 toolkit and admits each GPU command through the installed foreground CUDA controller. It configures and builds the `sm_70` targets first, then runs correctness, Compute Sanitizer memcheck, timing, and eligible profiler recipes serially. The coordinator itself does not reserve GPUs. Every executed native experiment receives an Nsight Systems capture; Nsight Compute runs only when replay is safe for that workload.

## Commands

Run a brief correctness diagnostic:

```bash
python benchmarks/run_suite.py --mode smoke --output-dir benchmark_runs
```

Run the complete finite sweep with focused profiling:

```bash
python benchmarks/run_suite.py --mode full --output-dir benchmark_runs
```

Select experiments or omit profiler captures:

```bash
python benchmarks/run_suite.py --mode full --output-dir benchmark_runs --experiments E01,E02,E09,E39 --profiles none
```

Add `--resume` to reuse records only when the source tree, built binaries, checked-in matrix, run mode, selected experiments, profiler policy, tool versions, and machine identity all match. A new run directory is created for each invocation. Resume reuses completed matching experiment records and continues the remaining work.

After a source or matrix change, start a fresh run rather than resuming older evidence. To repeat only the focused peer-transport measurements:

```bash
python benchmarks/run_suite.py --mode full --output-dir benchmark_runs --experiments E20,E21 --profiles focused
```

This selected run reports E20/E21 but cannot by itself establish all-forty campaign completion.

## Results

Each run directory contains `run_config.json`, `build.json`, `results.json`, `summary.json`, and `REPORT.md`. The report contains a disposition for every E00–E39 protocol; experiments not selected for a subset run and restricted hypotheses receive explicit `NOT_RUN` dispositions. Controller stdout/stderr, lease receipts, and profiler files are copied beneath `controller/`. Timing cases retain the raw samples and summaries in `results.json`.

Statuses follow `experiments/result.schema.json`: `GPU_RUN`, `CPU_ONLY`, `COMPILED_ONLY`, `NOT_RUN`, `REJECTED`, and `INCONCLUSIVE`. A failed correctness check, a controller timeout, a missing machine-readable result, sanitizer error summary, or failed requested capture is not reported as a passing measurement. Sanitizer completion requires an explicit zero-error summary in the selected tool's raw output even when the controller process exits successfully; the verification child's independent correctness checks must also pass. Profiler reports and summaries are checked from the controller receipt. Nsight Systems requires a nonempty report and captured GPU activity; kernel, memcpy, and memset row counts come from its SQLite report, so copy-only timelines qualify and an empty trace does not. Nsight Compute requires a nonempty report and raw CSV with `counter_valid=true`. A partial Nsight Compute analysis can still supply valid counters; its status and limits remain attached to the case. `smoke` uses one case and one sample except E32, which also checks its separately built child-launch case; smoke remains diagnostic only and defers private MPS startup in E31. `full` uses five warmups and thirty timing samples per matrix case. The short private MPS comparison starts and cleans up its campaign-owned server inside E31's admitted stage. E33 full timing and energy are reported only after telemetry establishes the required stable interval. E33's separate `--profile-diagnostic` Nsight Systems burst uses its own output directory and never establishes steady-state power or energy. E39 reports resident compute and complete-path medians/p95 and only matched, correctness-valid crossovers. A run with `--profiles none` is explicitly marked incomplete for native profiling.

## Tool paths and limits

The checked paths are CUDA 12.9 under `/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/cuda/12.9`, Nsight Systems 2025.3, and the installed Nsight Compute. The runner records each version check. It does not change device clocks, power limits, ECC, MPS configuration, or other persistent machine settings. E31's MPS work remains confined to the host runner's controller-admitted invocation and is inconclusive if private lifecycle checks do not pass. Unsupported public interfaces are reported with their reason. E04 and E27–E30 remain `NOT_RUN` because the protocols require restricted controls outside the public CUDA interface.

For E20, the full matrix enumerates all twelve directed device pairs. The controller receives all four inventoried GPU UUIDs; device and peer indices are interpreted inside the admitted visible-device list. E18/E19 request the inventoried physical GPU 0 and GPU 2 pair and use lease-local peer ordinals 0 and 1.
