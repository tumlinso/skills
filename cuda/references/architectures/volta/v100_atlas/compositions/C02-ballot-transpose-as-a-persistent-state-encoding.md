# C02 — Ballot transpose as a persistent state encoding

> Use lane-to-bit transposition once, then keep the result as the working representation.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** bitplanes, packing, state, FSM.
**Prerequisites:** M06 M04. **Evidence:** S03 S10.

## Construction [H; reachability C/P]


For lane values x_l with k bits, form p_j=Σ_l(((x_l>>j)&1)·2^l), j=0..k−1. These planes are sufficient to reconstruct every valid x_l. Execute several Boolean/threshold stages directly on p_j. Store or transmit only the planes required by the next consumer.

Choose explicitly whether planes are replicated in lanes or distributed across owner lanes. Replication makes independent word circuits easy but consumes redundant registers. Distribution reduces duplication and requires exchange for gates involving multiple planes.


## Why it could work

The transform is an exact permutation of bits, not approximate compression. It makes one hardware word the natural unit of structural logic. A mask from one stage is already the next stage input.

## Full cost and strongest baseline

Compare maintained bitplanes to repeated encode/decode and to scalar packed states. Count all initial ballots and ownership shuffles. Lower bit cardinality and longer reuse improve the economics; arbitrary floating state does not magically become small.

## Falsifier / rejection condition

Reject when each stage changes the semantic grouping or needs individual scalar values so often that the representation cannot persist.

**Experiment:** E01 E05 E13. This composition has not been benchmarked on a V100 here.
