# M04 — Shuffle as a constrained routing fabric

> Choose lane ownership so exchanging a value implements useful computation.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** routing, registers, graphs, transpose.
**Prerequisites:** R02 R06. **Evidence:** S03 S10.

## Established substrate [A; reachability C/P]

Shuffle exchanges register values among specified valid warp participants. It does not make a warp a flat arbitrarily indexed register file, and it does not fence unrelated memory. Wider payloads require additional movement.

## Appropriation hypothesis

Build butterflies, local graph gathers, small sorting/routing networks or fragment transposes. A lane can own a vertex or coefficient bank so its number is an address. Keep the layout expected by the next exchange rather than restoring row-major order after every stage.

## Cost and rejection boundary

Source lanes must participate and own defined values. Arbitrary traffic can require many shuffles; compare shared-memory broadcast or reloading cheap coefficients. A low-count network may lengthen dependencies or register lifetimes. Count useful multiword movement and code size, not just shuffle mnemonics.

## Next reads

Compositions: C03 C05 C16 C36. Experiments: E05 E09.
