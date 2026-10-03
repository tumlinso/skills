# C38 — Empirical conflict maps as placement hints

> Exploit a repeatable memory conflict without pretending its physical cause is fully known.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** HBM, L2, placement, measurement.
**Prerequisites:** M22 M21 R03 R12. **Evidence:** S04 S30.

## Construction [H; reachability C/P]


Measure address groups that contend under controlled parallel access. Use the result to permute independent state blocks or separate hot counters. Recheck after reallocations, page policy or driver changes.

The map is an empirical performance hint tied to allocation/conditions. Correctness must not depend on a supposed channel bit orL2slice. Keep a conventional layout fallback.


## Why it could work

An optimizer can exploit stable observable interference even before fully reconstructing the hash. This applies the same principle as bank-aware layout at a less documented scale.

## Full cost and strongest baseline

Control cache/TLB effects, request concurrency and alignment so the experiment discriminates possible causes. Training the map is a preprocessing cost. An improvement may come from translations rather than HBM distribution.

## Falsifier / rejection condition

Reject if the effect does not replicate across held-out patterns, if it disappears under real concurrency, or if retraining costs more than there used gain.

**Experiment:** E07 E08 E20 E39. This composition has not been benchmarked on a V100 here.
