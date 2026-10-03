# M14 — Register-resident local state machines

> Avoid turning a small evolving state into memory after every operation.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** registers, FSM, graph, state.
**Prerequisites:** R02 R11. **Evidence:** S01 S03 S04.

## Established substrate [D/E + H composition; reachability C/P]

Registers are per-thread storage with finite allocation/residency cost. Shuffle supplies a separate exchange contract. Dynamically indexed local arrays are not guaranteed to remain registers.

## Appropriation hypothesis

Hold a small graph patch, sequence context or actor×hidden-state block for many updates. Compile the local rule as a register circuit and encode identity in lane/bit position. Spill or stage only cold state and phase boundaries.

## Cost and rejection boundary

This trades capacity for locality. If every step requires arbitrary global interaction, the representation may duplicate state and add transfers. Cancellation, checkpointing and ownership changes need defined boundaries. Measure live registers, eligible work and reuse length.

## Next reads

Compositions: C05 C06 C35. Experiments: E16 E39.
