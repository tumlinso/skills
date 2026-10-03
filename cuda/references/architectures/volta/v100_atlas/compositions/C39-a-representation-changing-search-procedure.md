# C39 — A representation-changing search procedure

> For each new primitive, construct alternatives that move the problem to a different kind of machinery.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** design methodology, creative search, performance.
**Prerequisites:** R00 R11 R14 R15. **Evidence:** original synthesis; see linked mechanisms.

## Construction [H; reachability C/P]


Write the exact semantic operation, valid in put domain, output contract and required reuse. Then create at least three candidates: a strong conventional implementation; a representation-changing implementation; and an implementation using a different resource or information boundary.

Examples: CSR traversal versus register bitset graph versus owner-compute query; scalar transition versus bit-sliced circuit versus table lookup; SIMT transform versus tensor fragment versus precomputed basis routing. These are competing experiments, not a compulsory architecture.


## Why it could work

The procedure avoids optimizing a poor representation indefinitely. Every candidate is grounded in a primitive and a complete cost model, so extreme ideas can be retained without being promoted to facts.

## Full cost and strongest baseline

Track encode/decode, lifetime, precision, communication, progress, code size and strongest baseline. Prove exactness or declare approximation. Measure whole workload after isolated mechanisms. A new resource is not inherently a win.

## Falsifier / rejection condition

Reject candidates by explicit falsifiers and retain the reason in the ledger. Do not erase unconventional directions merely because the first shape failed, nor keep them alive by omitting their real cost.

**Experiment:** E38 E39. This composition has not been benchmarked on a V100 here.
