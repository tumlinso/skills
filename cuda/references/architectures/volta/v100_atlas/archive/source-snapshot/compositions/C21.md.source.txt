# C21 — Transmit support or deltas instead of dense state

> Choose the information boundary before choosing a faster transfer.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** NVLink, compression, support, delta.
**Prerequisites:** M06 M34 M35 R07. **Evidence:** S02 S25 S26.

## Construction [H; reachability C/P]


When a receiver already owns a valid base state, send changed positions plus values, or a support/frontier mask when only activity is needed. Include an epoch/base identifier and an explicit reset/resynchronization path. Bitplanes can be the wire format rather than an internal-only optimization.

Use density thresholds to switch to dense transfer when sparse metadata becomes larger. Keep the sparse and dense paths semantically identical; ordering and duplicate behavior must be defined.


## Why it could work

Only new information needs to cross the link. A word-level support representation can collapse many tiny signals into one payload and support direct receiver-side routing.

## Full cost and strongest baseline

Include detection, encoding, base-state maintenance, decoding and lost coalescing. A compressed transfer is not useful if the receiver immediately reconstructs an equally expensive dense object for every step.

## Falsifier / rejection condition

Reject when state ownership/epoch correctness is unproved, when changes are too dense, or when maintaining deltas costs more than moving the original representation.

**Experiment:** E13 E19 E39. This composition has not been benchmarked on a V100 here.
