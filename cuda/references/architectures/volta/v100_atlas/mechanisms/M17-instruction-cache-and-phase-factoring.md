# M17 — Instruction cache and phase factoring

> An enormous unrolled circuit can lose to a smaller stateful machine.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** instruction cache, unrolling, interpreter.
**Prerequisites:** R02 R10. **Evidence:** S04 S05.

## Established substrate [E; reachability C/B]

Original measurements identify multiple Volta instruction-cache levels. Code size, branch targets and repeated sequences can matter independently of data-cache behavior.

## Appropriation hypothesis

Factor repeated operations into compact phases; specialize the hot case and route rare complex transitions elsewhere. A small register-state interpreter can be a candidate when a fully unrolled palette stresses fetch and live state.

## Cost and rejection boundary

Dispatch, calls and lost cross-phase optimization can outweigh locality gains. Sweep footprint with equal work. A historical capacity is not a universal sharp threshold. Inspect instruction stalls and spills before blaming the code cache.

## Next reads

Compositions: C34. Experiments: E02 E30 E39.
