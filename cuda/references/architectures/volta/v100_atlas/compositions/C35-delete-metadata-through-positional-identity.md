# C35 — Delete metadata through positional identity

> Use lane, bit or local slot as an address when both ends share the mapping.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** metadata, layout, routing, compression.
**Prerequisites:** M02 M04 M14 R01. **Evidence:** S03 S10.

## Construction [H; reachability C/P]


Give a compact local object a stable positional identity: lane for vertex, bit for support member, register slot for small state component or block local position for coefficient. Define an explicit reversible map to external IDs only at boundaries.

Rank/select turns a mask into compact indexes when a boundary needs them. Avoid storing an index beside every value if the execution position already identifies it.


## Why it could work

The representation removes redundant information and its loads, address arithmetic and cache footprint. This is often a larger optimization than accelerating the metadata calculation itself.

## Full cost and strongest baseline

Mapping maintenance costs grow when objects are frequently reordered or deleted. Padding and boundary maps count. Physical SM IDs and transient warp IDs are not a stable external naming system.

## Falsifier / rejection condition

Reject when reorganization requires rebuilding maps every step, or when positional assumptions become hidden correctness dependencies that consumers cannot honor.

**Experiment:** E05 E13 E39. This composition has not been benchmarked on a V100 here.
