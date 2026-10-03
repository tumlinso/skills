# E21 — Host NUMA ingress

> Can locality remove cross-socket traffic or supply independent host paths?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, host, numa, ingress.
**Prerequisites:** R12. **Evidence:** S30 S33 S36.

**Question:** Can locality remove cross-socket traffic or supply independent host paths?

**Minimal setup:** Place and verify host pages on each NUMA node, register/pin them, then transfer to each GPU with controlled producer affinity.

**Sweep:** Local/remote pages, individual/simultaneous directions and mapped versus staged access.

**Discriminating observation:** Latency/bandwidth differences explained by page placement and root topology.

**Baseline:** Conventional pinned transfers with verified local placement.

**Confounders / correctness:** Pinning and thread affinity do not prove page locality; existing data may originate remotely.

**Access gate:** Read-only topology inspection and supported OS allocation/registration.

**Related:** C23 M43 M44.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
