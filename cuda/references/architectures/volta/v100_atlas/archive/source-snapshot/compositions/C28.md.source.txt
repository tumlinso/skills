# C28 — Dependent QMDs as a bounded dataflow experiment

> Explore the launch front end only after public graph replay is a measured baseline.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** QMD, launch, dataflow, driver.
**Prerequisites:** M39 M38 M33 R09 R06. **Evidence:** S27 S13 S40.

## Construction [S; reachability K]


Start from two finite kernels with known buffers and one explicit dependency. Investigate documented descriptor dependency/release fields and queue ownership. Determine address units, resource fields, reference counts, visibility and completion semantics from implementation evidence before constructing commands.

Only after that minimal case would circular queues or longer bounded phases be meaningful experiments. Do not rewrite live CUDA-owned descriptors or equate an SM-mask field with ordinary CUDA affinity.


## Why it could work

The header proves richer control objects exist below the familiar launch API. It leaves open whether a useful restricted dataflow schedule can reduce CPU/SM orchestration overhead on this platform.

## Full cost and strongest baseline

Public graphs and batched launches are the strongest baselines. Setup, firmware validation and driver ownership can dominate. No arbitrary self-modifying runtime or cross GPU work migration is established.

## Falsifier / rejection condition

Reject if operational contracts remain unknown, if safety requires unsupported ownership violations, or if the minimal case cannot outperform public graph replay at equal semantics.

**Experiment:** E29 E32. This composition has not been benchmarked on a V100 here.
