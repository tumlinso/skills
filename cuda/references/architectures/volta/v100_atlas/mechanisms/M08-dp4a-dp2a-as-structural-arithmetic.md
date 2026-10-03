# M08 — DP4A/DP2A as structural arithmetic

> Use packed integer dots without assuming integer tensor-core support on GV100.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** DP4A, integer, counting, quantization.
**Prerequisites:** R04 R15. **Evidence:** S03 S05 S08.

## Established substrate [A/D; reachability C/P]

Packed dot forms multiply byte/halfword components and accumulate under signedness-specific integer semantics. These are distinct from later documented integer tensor operations. Actual instruction selection needs the exact sm70 form.

## Appropriation hypothesis

Encode short category scores, correlations or bounded counts directly as packed inputs. Preserve integer exactness where floating expansion would be unnecessary. Several score channels can reuse one packed operand; coordinate the instruction stream with other useful work only after measuring shared issue costs.

## Cost and rejection boundary

A dot collapses products; it does not preserve four independent outputs. Prove accumulator range and sign extension. Packing dominates some one-shot uses. Pure binary intersections should be compared with AND+POPC, not an artificially slow scalar loop. Wider integer tensor forms must not be imported by family name.

## Next reads

Compositions: C08 C11. Experiments: E13 E03.
