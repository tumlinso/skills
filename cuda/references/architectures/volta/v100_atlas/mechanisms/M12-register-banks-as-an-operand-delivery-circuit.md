# M12 — Register banks as an operand-delivery circuit

> Storage placement can matter even when the arithmetic is unchanged.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** register banks, SASS, reuse.
**Prerequisites:** R02 R10. **Evidence:** S04 S05 S11.

## Established substrate [E/R; reachability C/B]

Original Volta measurements identify parity-selected banks and some three-source conflicts. Reuse changes the actual reads. This is empirical microarchitecture, not a PTX allocation contract.

## Appropriation hypothesis

Model each hot instruction as a source-read hyper edge. Arrange operands or introduce an amortized copy so recurring reads fit the bank supply. Choose a tile layout partly by how it feeds arithmetic, not only how it loads from memory.

## Cost and rejection boundary

Compiler register assignment may defeat source-level parity intentions. Binary renaming must update all uses and metadata. A fix can increase live ranges and reduce occupancy. Hold mathematical work and operating conditions constant before attributing a gain to banks.

## Next reads

Compositions: C17 C16. Experiments: E04 E30.
