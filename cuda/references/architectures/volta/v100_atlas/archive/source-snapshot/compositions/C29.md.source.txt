# C29 — A doubled virtual ring without duplicate payload

> Use two legal views of one backing region to remove split-window handling.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** VMM, alias, ring, addressing.
**Prerequisites:** M40 R08 R06. **Evidence:** S18 S31.

## Construction [H; reachability C/P]


Reserve a2N virtual interval and investigate mapping the sa meN backing bytes into both halves. A window of length≤N starting in the first half could then be virtually contiguous even when it wraps the physical ring. Align N to required granularity and establish the legal alias/cache contract.

Keep producer/consumer ownership and epoch synchronization exactly as explicit as in a conventional ring. This transformation changes addressing, not concurrency semantics.


## Why it could work

Virtual address layout can remove modulo or two-segment handling without copying the payload. It can be useful for repeated windows when the consumer accepts the mapped view directly.

## Full cost and strongest baseline

Compare two-pointer windows and simple modulo, which may already compile cheaply. Mapping setup, VA footprint, TLB behavior and any coherence restrictions count. Aliasing is not assumed safe merely because both mappings succeed.

## Falsifier / rejection condition

Reject when the installed V MM contract cannot support the intended use, when concurrent aliases lack a proof, or when translation cost exceeds saved address work.

**Experiment:** E23 E08. This composition has not been benchmarked on a V100 here.
