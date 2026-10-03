# C26 — Component remapping in the copy engine

> Investigate moving a fixed record format directly into its consumer representation.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** DMA, format, remap, non-SM.
**Prerequisites:** M37 M36 R09. **Evidence:** S12 S15.

## Construction [H; reachability K]


Use the documented copy-class component controls as a research target: select source components, insert supported constants or suppress selected outputs while copying between supported pitched/linear layouts. Begin with a small fixed-width record transformation whose CPU reference is unambiguous.

Establish a valid owned driver/channel route and all field units before issuing anything. Public DMA plus a shader transform remains the initial executable baseline. Existing UVM fill remapping is evidence of the machinery, not of a complete general-purpose public API.


## Why it could work

If reachable at acceptable cost, the engine could transform data while SMs perform other useful work. Removing a separate read/write formatting pass could matter more than saving arithmetic.

## Full cost and strongest baseline

Compare a fused SM copy/transform and ordinary copy+transform. Include command construction, launch latency and shared HBM contention. Component remap is restricted; it is not arbitrary AoS↔SoA, gather or permutation.

## Falsifier / rejection condition

Reject if the required layout is not expressible, if a safe reachable interface cannot be established, or if setup and interference exceed the saved pass.

**Experiment:** E27 E17. This composition has not been benchmarked on a V100 here.
