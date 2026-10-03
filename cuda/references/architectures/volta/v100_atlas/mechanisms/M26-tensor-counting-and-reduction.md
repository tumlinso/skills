# M26 — Tensor counting and reduction

> Use ordinary algebra to encode structure, without imagining arbitrary semiring hardware.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** tensor, counting, reduction, support.
**Prerequisites:** R05 R15. **Evidence:** S03 S19 S20.

## Established substrate [A/E + H encodings; reachability P/C]

Binary0/1 products can represent conjunction and sums can represent counts. Prior work maps reductions/scans to tensor operations. This does not turn MMA into native Boolean, min-plus or arbitrary semiring execution.

## Appropriation hypothesis

Compute many shared-neighbor counts or category correlations with reused small dense blocks. Use a coarse score to route ambiguous cases to an exact bitset/integer stage. Repeated coefficient/state reuse can make structured numeric work attractive.

## Cost and rejection boundary

AND+POPC, DP4A and shuffle trees are strong baselines. Expanding bits to half, zero-work and output extraction can erase nominal throughput. Exactness requires a validated bounded numeric domain; CPU matrix identities do not establish tensor rounding.

## Next reads

Compositions: C11 C12 C14. Experiments: E10 E11 E12.
