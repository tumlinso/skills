# M45 — Contexts, IPC and MPS

> Multiplexing resources does not merge program semantics.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** contexts, MPS, IPC, isolation.
**Prerequisites:** R10 R06. **Evidence:** S01 S30 S41.

## Established substrate [A/D version-bound; reachability C]

Contexts own VA/module/execution state; IPC shares selected resources under explicit contracts. Volta MPS supports separate address spaces, not universal fatal fault isolation. Current MPS interfaces include newer variants not assumed on R580.

## Appropriation hypothesis

Use sharing/isolation deliberately for long lived services or independent work. IPC can separate control processes while preserving chosen data lifetimes. MPS is a precedent for multiplexing, not multi GPU aggregation.

## Cost and rejection boundary

Pointer identity, lifetime, fault scope and capture behavior change across processes. Resource percentages are not fairness/latency guarantees. Measure interference with the installed compatible version. Concurrent clients contaminate microbenchmarks.

## Next reads

Compositions: C25 C32. Experiments: E31 E36.
