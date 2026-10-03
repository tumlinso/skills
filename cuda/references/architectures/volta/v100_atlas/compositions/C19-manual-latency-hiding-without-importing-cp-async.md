# C19 — Manual latency hiding without importing cp.async

> Build a Volta pipeline from early loads, independent work, shared stages or DMA.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** prefetch, persistent, DMA, latency hiding.
**Prerequisites:** M15 M16 M19 M36 R06. **Evidence:** S01 S30 S15.

## Construction [H; reachability C/P]


Issue ordinary future loads early into registers while computing on current data. For block reuse, stage into shared memory and publish at a valid phase boundary. Alternatively, let a copy engine fill a later buffer under supported stream/event ordering.

A loader-warp role is an option, not a requirement. Compare it to each compute warp prefetching its own next work. Choose buffer depth from latency, bandwidth and live-state cost.


## Why it could work

The schedule creates independent useful work between request and use. It supplies the purpose of an asynchronous pipeline without claiming later cp.async/mbarrier semantics exist on Volta.

## Full cost and strongest baseline

Early loads consume registers and request slots. Additional buffers consume memory and synchronize. Copy and compute share HBM; specialized warps may sit idle under skew.

## Falsifier / rejection condition

Reject if the pipeline cannot prove producer progress/visibility, if stalls simply move to another boundary, or if register/buffer pressure costs more than the hidden latency.

**Experiment:** E03 E06 E16 E17. This composition has not been benchmarked on a V100 here.
