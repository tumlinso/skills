# Experiment cards and current evidence

The cards preserve the protocols authored at [`5c1f805`](https://github.com/tumlinso/gpu_circuit_bending_atlas/tree/5c1f805db80a81f7476ede8292abba69821d104f). Their original authoring status was `NOT_RUN_ON_GPU`; current status labels describe the subset implemented in campaign `v100-20261006T145155Z-4bd01216`, sourced from `f223c51dcfacab602e9bc68b3e65cc75730dc7f8`.

Use the [claim-limits index](CLAIM_LIMITS.md) for a cross-cutting view of what the current run does not establish. Read [how to interpret results](INTERPRETING_RESULTS.md), the [portable campaign provenance](evidence/v100-20261006/provenance.json), and the [campaign report](../archive/campaign/REPORT.source.txt) for context. The compact summaries retain each measured case's configuration, status, checks, metrics, limitations, sample counts, and raw-artifact locators. The raw measurement vectors, controller receipts, and profiler files remain local under `benchmark_runs/` and are not in Git. Each card links to its summary and the local full report.

| ID | Current disposition | Card | Portable evidence |
|---|---|---|---|
| E00 | CPU_ONLY | [E00](E00-inventory-and-capability-gates.md) | [summary](evidence/v100-20261006/E00.json) |
| E01 | CPU_ONLY | [E01](E01-algebra-and-encoding-checks.md) | [summary](evidence/v100-20261006/E01.json) |
| E02 | GPU_RUN | [E02](E02-instruction-latency-versus-throughput.md) | [summary](evidence/v100-20261006/E02.json) |
| E03 | GPU_RUN | [E03](E03-cross-pipeline-interference.md) | [summary](evidence/v100-20261006/E03.json) |
| E04 | NOT_RUN | [E04](E04-register-bank-and-operand-reuse-effects.md) | [summary](evidence/v100-20261006/E04.json) |
| E05 | GPU_RUN | [E05](E05-warp-routing-matching-and-lookup.md) | [summary](evidence/v100-20261006/E05.json) |
| E06 | GPU_RUN | [E06](E06-shared-banks-and-phase-pipelines.md) | [summary](evidence/v100-20261006/E06.json) |
| E07 | GPU_RUN | [E07](E07-cache-and-transaction-accounting.md) | [summary](evidence/v100-20261006/E07.json) |
| E08 | GPU_RUN | [E08](E08-translation-working-sets-and-pages.md) | [summary](evidence/v100-20261006/E08.json) |
| E09 | GPU_RUN | [E09](E09-mma-lane-and-register-ownership.md) | [summary](evidence/v100-20261006/E09.json) |
| E10 | GPU_RUN | [E10](E10-tensor-numerical-fingerprint.md) | [summary](evidence/v100-20261006/E10.json) |
| E11 | GPU_RUN | [E11](E11-tensor-versus-bitset-intersections.md) | [summary](evidence/v100-20261006/E11.json) |
| E12 | GPU_RUN | [E12](E12-tensor-circuits-versus-structured-simt.md) | [summary](evidence/v100-20261006/E12.json) |
| E13 | GPU_RUN | [E13](E13-representation-crossover.md) | [summary](evidence/v100-20261006/E13.json) |
| E14 | GPU_RUN | [E14](E14-atomics-as-useful-coordination.md) | [summary](evidence/v100-20261006/E14.json) |
| E15 | GPU_RUN | [E15](E15-publication-and-progress-litmus.md) | [summary](evidence/v100-20261006/E15.json) |
| E16 | GPU_RUN | [E16](E16-persistent-roles-and-residency.md) | [summary](evidence/v100-20261006/E16.json) |
| E17 | GPU_RUN | [E17](E17-dma-and-compute-overlap.md) | [summary](evidence/v100-20261006/E17.json) |
| E18 | GPU_RUN | [E18](E18-peer-loads-cache-behavior-and-latency.md) | [summary](evidence/v100-20261006/E18.json) |
| E19 | GPU_RUN | [E19](E19-peer-signaling-and-clock-relationships.md) | [summary](evidence/v100-20261006/E19.json) |
| E20 | GPU_RUN | [E20](E20-actual-nvlink-routing-and-saturation.md) | [summary](evidence/v100-20261006/E20.json) |
| E21 | GPU_RUN | [E21](E21-host-numa-ingress.md) | [summary](evidence/v100-20261006/E21.json) |
| E22 | GPU_RUN | [E22](E22-stream-memory-operations.md) | [summary](evidence/v100-20261006/E22.json) |
| E23 | GPU_RUN | [E23](E23-vmm-alias-and-view-behavior.md) | [summary](evidence/v100-20261006/E23.json) |
| E24 | GPU_RUN | [E24](E24-fault-and-access-counter-policy.md) | [summary](evidence/v100-20261006/E24.json) |
| E25 | GPU_RUN | [E25](E25-feedback-cost-and-regret.md) | [summary](evidence/v100-20261006/E25.json) |
| E26 | GPU_RUN | [E26](E26-texture-and-sfu-approximation.md) | [summary](evidence/v100-20261006/E26.json) |
| E27 | NOT_RUN | [E27](E27-copy-remap-reachability.md) | [summary](evidence/v100-20261006/E27.json) |
| E28 | NOT_RUN | [E28](E28-copy-engine-semaphore-actor.md) | [summary](evidence/v100-20261006/E28.json) |
| E29 | NOT_RUN | [E29](E29-dependent-qmd-minimal-experiment.md) | [summary](evidence/v100-20261006/E29.json) |
| E30 | NOT_RUN | [E30](E30-binary-transformation-validation.md) | [summary](evidence/v100-20261006/E30.json) |
| E31 | GPU_RUN | [E31](E31-mps-and-process-interference.md) | [summary](evidence/v100-20261006/E31.json) |
| E32 | GPU_RUN | [E32](E32-launch-graphs-and-cdp.md) | [summary](evidence/v100-20261006/E32.json) |
| E33 | GPU_RUN | [E33](E33-power-and-steady-state-behavior.md) | [summary](evidence/v100-20261006/E33.json) |
| E34 | CPU_ONLY | [E34](E34-ras-contamination-audit.md) | [summary](evidence/v100-20261006/E34.json) |
| E35 | CPU_ONLY | [E35](E35-platform-and-electrical-evidence.md) | [summary](evidence/v100-20261006/E35.json) |
| E36 | CPU_ONLY | [E36](E36-toolchain-and-library-compatibility.md) | [summary](evidence/v100-20261006/E36.json) |
| E37 | GPU_RUN | [E37](E37-new-ptx-spelling-on-old-silicon.md) | [summary](evidence/v100-20261006/E37.json) |
| E38 | CPU_ONLY | [E38](E38-negative-space-falsification.md) | [summary](evidence/v100-20261006/E38.json) |
| E39 | GPU_RUN | [E39](E39-complete-composition-usefulness.md) | [summary](evidence/v100-20261006/E39.json) |
