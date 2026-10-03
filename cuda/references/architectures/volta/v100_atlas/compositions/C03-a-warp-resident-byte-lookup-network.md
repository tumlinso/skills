# C03 — A warp-resident byte lookup network

> Build a small exact table from register owners, shuffle and byte selection.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** lookup, PRMT, registers, routing.
**Prerequisites:** M03 M04 M14. **Evidence:** S03 S08 S10.

## Construction [H; reachability C/P]


A128-byte immutable table fits as one 32-bit word per lane. For index i∈[0,127], owner=i>>2 and byte offset=i&3. Shuffle the owner word to the requesting lane and extract the chosen byte. An eight-entry byte table can instead occupy two registers in each lane, with PRMT selecting several entries.

Larger tables require several words per owner and a second selection stage. Make that stage explicit: a dynamically indexed local array can spill rather than act like a register RAM. Choose replicated versus distributed tables by reuse and query correlation.


## Why it could work

Lane number becomes a coarse table address. The hardware exchange routes a whole packed word; extraction supplies the fine address. The scalar memory hierarchy is not used for each lookup once the table is loaded.

## Full cost and strongest baseline

Compare shared-memory tables, constant broadcast and cached global loads. Count table loading, register capacity and shuffle width. A uniform query can strongly favor constant memory. A partially participating warp needs a different ownership arrangement.

## Falsifier / rejection condition

Reject when updates are frequent, table size forces expensive register selection, or missing owners violate the collective contract. Test every index and byte ordering.

**Experiment:** E01 E05 E13. This composition has not been benchmarked on a V100 here.
