# C24 — Monotone atomic fixed-point computation

> For the right algebra, duplicates and execution order can stop being correctness problems.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** atomics, dataflow, graph, fixed point.
**Prerequisites:** M29 M21 M30 R06. **Evidence:** S03 S30.

## Construction [H; reachability C/P]


Choose a state domain with an associative, commutative, idempotent merge and a monotone update. Examples include accumulating reachability bits by OR or suitable bounded min/max propagation. A successful change can enqueue affected neighbors; duplicate proposals merge harmlessly.

State clearly whether the domain is finite-height or otherwise convergent, and how fairness ensures relevant updates occur. Termination must account for queued and in-flight work, not merely an empty local frontier.


## Why it could work

Idempotence can trade rigid lockstep for redundant but harmless work. Atomics embody the merge itself rather than only protecting an unrelated critical section. This is a mathematical change to the coordination problem.

## Full cost and strongest baseline

Compare synchronized frontiers and locally aggregated proposals. Duplicate work, hot targets and termination detection can erase the gain. Floating addition and overwrite are not idempotent, so ordinary dynamical integration does not automatically qualify.

## Falsifier / rejection condition

Reject if the update is non monotone, if stale state changes the fixed point, or if progress/termination is not established. A convergent equation alone is not a schedulable implementation.

**Experiment:** E01 E14 E15 E39. This composition has not been benchmarked on a V100 here.
