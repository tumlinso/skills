# C05 — A32-vertex graph carried in warp registers

> Turn a small graph step into intersection tests and a ballot.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** graph, support, frontier, registers.
**Prerequisites:** M01 M02 M04 M14. **Evidence:** S03 S08 S10.

## Construction [H; reachability C/P]


Assign vertex l to lane l. Store its incoming-neighbor mask N_l as one word. Let F be a replicated frontier mask. Then next_l=((N_l & F)!=0), and a ballot of next_l gives the next frontier. Visited filtering is another mask operation.

This computes incoming propagation: using outgoing masks without changing the equation reverses the intended relation. For weighted or multi dimensional state, retain the support mask but introduce the actual numeric update separately. Graph patches can be connected by compact boundary messages.


## Why it could work

The adjacency row is a register and the frontier is a shared structural word. No per-edge pointer, explicit edge loop or intermediate Boolean array is required for a local unweighted step.

## Full cost and strongest baseline

Compare compact CSR and bitset baselines, including graph load and patch-boundary exchange. The fixed32-vertex geometry creates padding for small patches and partitioning cost for large ones. Useful reuse across many steps is the major opportunity.

## Falsifier / rejection condition

Reject when graph topology changes too frequently, when most edges cross patches, or when the actual update is not reducible to the proposed support operation.

**Experiment:** E01 E13 E39. This composition has not been benchmarked on a V100 here.
