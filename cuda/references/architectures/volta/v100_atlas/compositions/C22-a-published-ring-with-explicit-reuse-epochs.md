# C22 — A published ring with explicit reuse epochs

> Build the synchronization protocol before optimizing the flag instruction.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** queue, semaphore, publication, progress.
**Prerequisites:** M29 M31 M35 R06. **Evidence:** S17 S25 S30 S42.

## Construction [H; reachability C/P]


Model each slot through free→reserved→published→consumed→reusable. Reservation grants a writer exclusive space; payload writes precede release publication. A reader acquire-observes the matching epoch before reading, and publishes reuse only after finishing. Bound counter distance across wraparound.

Use a separate validity/sequence word when necessary to distinguish reused slots. A group reservation can allocate several slots, but completion of the group still requires its own rule. Define shutdown, cancellation and backpressure.


## Why it could work

The state machine prevents readers from confusing reservation with completed payload and writers from overwriting unconsumed data. It can be embodied by supported atomics or stream-memory operations at the correct scope.

## Full cost and strongest baseline

Compare established device/peer queue protocols. Count polling traffic, fences, slot padding and latency tails. A command wait may save an SM but can introduce a submission-graph dependency invisible to CUDA.

## Falsifier / rejection condition

Reject without a participation, visibility and progress proof. Tests are only falsifiers. In particular, a consumer occupying all producer resources is invalid regardless of how fast the atomic is.

**Experiment:** E15 E19 E22. This composition has not been benchmarked on a V100 here.
