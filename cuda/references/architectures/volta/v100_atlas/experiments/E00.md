# E00 — Inventory and capability gates

> What exact machine and reachable feature set do these experiments target?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
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
