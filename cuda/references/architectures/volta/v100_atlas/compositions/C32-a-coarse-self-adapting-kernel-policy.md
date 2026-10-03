# C32 — A coarse self-adapting kernel policy

> Use a small validated choice set and make observation cost explicit.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** adaptation, counters, policy, latency.
**Prerequisites:** M46 M42 M47 R11 R12. **Evidence:** S34 S35 S36 S29.

## Construction [H; reachability C/P]


Choose among several already-correct representations or tile policies using epoch duration, queue depth, density or supported counters. Apply hysteresis and a minimum residence time. Switch only when q·estimated_saving exceeds observation+switch+repack cost plus an uncertainty margin, where q is expected remaining reuse.

Maintain a fixed-policy control and log why a choice changed. Use the cheapest signal that predicts the relevant resource bottleneck.


## Why it could work

Workload phases can change the best representation. Feedback can exploit this without putting a heavyweight optimizer in every warp. The policy selects among verified kernels; it does not invent unsafe synchronization at runtime.

## Full cost and strongest baseline

Include lag, noise, cold state and measurement perturbation. Some profilers replay kernels and are unsuitable as live feedback. A tiny density heuristic may beat a rich counter model.

## Falsifier / rejection condition

Reject when adaptation has worse regret than a fixed policy, when measurement dominates, or when oscillation repeatedly destroys locality.

**Experiment:** E25 E39. This composition has not been benchmarked on a V100 here.
