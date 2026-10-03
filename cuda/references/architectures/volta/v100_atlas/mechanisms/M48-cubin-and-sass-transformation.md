# M48 — Cubin and SASS transformation

> Machine-code experiments need complete executable evidence.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** SASS, cubin, compiler, rewriting.
**Prerequisites:** R10 R02 R06. **Evidence:** S04 S05 S11.

## Established substrate [D/R; reachability B]

Binary tools and original reverse engineering expose register assignment, opcodes and control metadata. PTX registers are not physical allocation. Code containers carry more than instruction bytes.

## Appropriation hypothesis

Test precise operand placement, schedules, dispatch or forms the compiler does not emit. A validated local transformation can become a reusable experiment primitive. Keep the compiler binary as control.

## Cost and rejection boundary

Branch/call targets, relocations, constants, globals, resources and dependencies must remain consistent. Passing one random test does not prove variable delay correctness. Pin versions/hashes and preserve the rollback path. No arbitrary kernel rewriter is claimed.

## Next reads

Compositions: C17 C34 C39. Experiments: E30 E37.
