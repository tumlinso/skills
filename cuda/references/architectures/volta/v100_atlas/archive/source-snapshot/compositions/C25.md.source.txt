# C25 — A resident micro service with a finite operator palette

> Preserve hot computational state while consuming compact task descriptions.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** persistent, scheduler, FSM, latency.
**Prerequisites:** M30 M15 M14 M17 R06. **Evidence:** S30 S01.

## Construction [H; reachability C/P]


Select a small family of operations sharing useful register/shared state. A long-lived executor consumes bounded descriptors, groups compatible work and emits completion records. Use local batching before global work stealing. Define stop/drain and descriptor lifetime.

An operator palette can be a handful of graph/state transforms, not a general virtual machine. Keep rare complex cases on another path so the hot executor remains small.


## Why it could work

Launch and state reload costs can be amortized across many tiny tasks. The scheduler becomes part of the data representation: compact task IDs identify already resident coefficients and layouts.

## Full cost and strongest baseline

Compare graphs, proper batching and fused kernels. Queue traffic, dispatch divergence, idle reservations and instruction footprint count. A resident kernel can reduce available capacity for its own producer.

## Falsifier / rejection condition

Reject when tasks are already large enough to amortize launches, when the palette fragments control excessively, or when progress depends on unspecified concurrent scheduling.

**Experiment:** E16 E32 E39. This composition has not been benchmarked on a V100 here.
