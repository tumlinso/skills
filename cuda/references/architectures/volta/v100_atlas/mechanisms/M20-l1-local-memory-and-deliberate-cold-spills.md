# M20 — L1, local memory and deliberate cold spills

> The right question is useful residency, not zero spills at any cost.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** L1, spills, occupancy.
**Prerequisites:** R03. **Evidence:** S01 S04 S30.

## Established substrate [A/D/E; reachability C/P]

Local memory is memory-backed storage with caching, not extra registers. Register allocation and shared/L1 choices interact and can create residency cliffs.

## Appropriation hypothesis

Keep hot fields explicit in registers and allow rare state to live locally/shared. A few predictable cold loads may permit enough additional independent work to hide latency. Separate routing metadata from streaming payload to reduce pollution.

## Cost and rejection boundary

Uncontrolled spills in the hot loop can multiply traffic. Source array size does not reveal actual register use. Record local loads/stores, cache behavior and total time. Changing carveout can improve one path while harming another.

## Next reads

Compositions: C19 C35. Experiments: E07 E16.
