# E00 — Inventory and capability gates

> What exact machine and reachable feature set do these experiments target?

**Status:** CPU_ONLY. **Original protocol status:** NOT_RUN_ON_GPU. **Original archive:** [commit `5c1f805db80a81f7476ede8292abba69821d104f`](https://github.com/tumlinso/gpu_circuit_bending_atlas/commit/5c1f805db80a81f7476ede8292abba69821d104f). **Depth:** 4.
**Read when:** experiment, inventory, and, capability, gates.
**Prerequisites:** R12. **Evidence:** S32 S36 S42.

**Question:** What exact machine and reachable feature set do these experiments target?

**Minimal setup:** Run the supplied read-only Driver API probe plus UUID/BDF, topology, PCIe, NUMA and link-state inspection. Save raw outputs before allocating benchmark buffers.

**Sweep:** Every device and ordered pair; compiler and driver versions separately; idle and steady-load telemetry.

**Discriminating observation:** A capability matrix that distinguishes physical identity, peer access, native atomics, VMM, managed memory and stream operations.

**Baseline:** No performance baseline; compare reported inventory to assumptions in a candidate design.

**Confounders / correctness:** Device ordinals can change. A supported flag is not an achieved-performance measurement. Do not reset, enable peers or change clocks as part of inventory.

**Access gate:** Public read-only queries; errors must be retained, not treated as false or zero.

**Related:** R01 R07 R10 R13.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


## Measured coverage (2026-10-06)

Read-only host inventory was run once. It recorded four devices (`device_count=4`) and reported capability/inventory fields; no memory allocation, peer enabling, kernel launch or clock change occurred. No timing statistic applies. Implementation: [`_inventory`](../scripts/atlas_host.py#L92) and [`capability_probe.cpp`](../benchmarks/capability_probe.cpp#L1). [Measured summary](evidence/v100-20261006/E00.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md)

## Meaning through representation and execution

- Supports: Reported host inventory and capability-query results for this run.
- Design implication (inference): Use reported capabilities to exclude unreachable mechanisms from candidate designs before performance work.
- Does not establish: Achieved peer transfer, memory bandwidth, atomics under load, link routing, power behavior or any kernel performance.
- Original protocol gaps: The all-device ordered-pair inventory and idle/steady-load telemetry sweep were not performed.
