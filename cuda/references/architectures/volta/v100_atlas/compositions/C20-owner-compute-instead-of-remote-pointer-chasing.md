# C20 — Owner-compute instead of remote pointer chasing

> Send a compact question to where the large state already lives.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** NVLink, graph, owner compute, communication.
**Prerequisites:** M34 M35 M30 R06 R07. **Evidence:** S02 S25 S26.

## Construction [H; reachability C/P]


Compare three implementations of the same query: requester gathers remote data; requester stages a bulk region and computes; or a resident owner service receives a compact descriptor, computes locally and returns a reduced answer. The owner can cache support/coefficient state across many queries.

The service is a software queue plus a schedulable kernel, not a hardware remote-function call. Batch compatible requests and keep reply ownership explicit. Use direct remote loads for tiny control fields only when their contract and latency make sense.


## Why it could work

Communication cost can fall from many irregular payload reads to a descriptor and a small result. This exploits information reduction rather than only higher link bandwidth.

## Full cost and strongest baseline

Include enqueue, publication, service admission, load balance, completion and reply latency. The owner competes with its local work for HBM/SMs. Direct pull may win for rare small reads; staging may win for repeated dense reuse.

## Falsifier / rejection condition

Reject when service overhead exceeds payload savings, when imbalance dominates, or when waiting actors can starve the service producer. No remote-cache assumption is required for the comparison.

**Experiment:** E18 E19 E16 E39. This composition has not been benchmarked on a V100 here.
