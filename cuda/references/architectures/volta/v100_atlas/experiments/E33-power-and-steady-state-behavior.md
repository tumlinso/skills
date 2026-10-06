# E33 — Power and steady-state behavior

> Is the proposed schedule faster after thermal and power transients settle?

**Status:** GPU_RUN (subset: two resident synthetic schedules under stable intervals). **Original protocol status:** NOT_RUN_ON_GPU ([archived E33 at commit 5c1f805db80a](https://github.com/tumlinso/gpu_circuit_bending_atlas/blob/5c1f805db80a81f7476ede8292abba69821d104f/experiments/E33.md)). **Depth:** 4.
**Read when:** experiment, power, and, steady-state, behavior.
**Prerequisites:** R12. **Evidence:** S02 S36.

**Question:** Is the proposed schedule faster after thermal and power transients settle?

**Minimal setup:** Run equal-work schedules to stable conditions under unchanged supported limits; record clocks, temperature, power and useful outputs.

**Sweep:** Overlap ratio, phase order, neighbor activity and workload duration.

**Discriminating observation:** Sustained throughput and energy per result with raw telemetry context.

**Baseline:** Maximum-overlap and simple fixed schedules.

**Confounders / correctness:** Sensor averaging, ambient changes and reduced precision/work can manufacture apparent gains.

**Access gate:** No voltage/firmware modifications or unsafe power-limit changes.

**Related:** C33 M52.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.

## Measured coverage (2026-10-06)

The synthetic E03 kernel launched 1,048,576 threads; each event performed 100,000 uint32 `add.u32 x,x,1` operations and 100,000 single-precision `fmaf(f,1.0001f,0.0003f)` operations per thread. The serial policy ran the independent add and FMA loops separately; the interleaved policy alternated their independent operations. That is 209,715,200,000 launched work units per event. With clocks and power settings unchanged, serial and interleaved schedules each ran for 150 seconds. The primary timing selected complete events within four contiguous stable 30-second windows: 7,739 serial and 8,297 interleaved events, with median event times 15.508480 ms and 14.522368 ms. Read-only telemetry estimated 28.95 kJ and 29.04 kJ over the respective stable intervals. The runs were sequential; telemetry was not hardware-calibrated and policy order was not randomized. Full resident sample vectors are retained, while primary summaries use stable-window matches.

Primary scope: host [_run_e33_resident](../scripts/atlas_host.py#L864) selects events from [run_e03_steady](../benchmarks/native/logic.cu#L268) and its [pipeline_kernel](../benchmarks/native/logic.cu#L203). See the [serial resident record](evidence/v100-20261006/E33-raw-host-records.md) and [interleaved resident record](evidence/v100-20261006/E33-raw-host-records.md); `host-profile/E33` is a separate Nsight diagnostic, not the stable-window source.

[Measured summary](evidence/v100-20261006/E33.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md)

## Meaning through representation and execution

- **Supports:** the selected stable-window event medians and read-only energy estimates for these two sequential synthetic runs.
- **Design implication (inference):** retain full traces and predefine stability windows when comparing long-running schedules; report the stable-window selection rule with the summary.
- **Does not establish:** a randomized schedule effect, calibrated energy per useful result, thermal independence, or broad steady-state superiority.
- **Original protocol gaps:** overlap-ratio, phase-order, neighbor-activity, and workload-duration sweeps were not performed; sequential order and window comparability remain limits.
