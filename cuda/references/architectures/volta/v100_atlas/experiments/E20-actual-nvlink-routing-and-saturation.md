# E20 — Actual NVLink routing and saturation

> Which links carry the traffic, and where does it saturate?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, actual, nvlink, routing, and, saturation.
**Prerequisites:** R12. **Evidence:** S02 S36 S26.

**Question:** Which links carry the traffic, and where does it saturate?

**Minimal setup:** Inventory link connectivity and run directed pair transfers with available link/PCIe telemetry.

**Sweep:** One-way, two-way, multiple streams, all pair combinations and concurrent owner compute.

**Discriminating observation:** Measured directional bandwidth and interference tied to the actual topology.

**Baseline:** Each isolated direct pair and supported alternative staging path.

**Confounders / correctness:** Bidirectional aggregates cannot be compared with one-way payload rates; counters may include protocol traffic.

**Access gate:** No assumed multi-hop forwarding or six-links-per-pair topology.

**Related:** R07 C23 M22.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
