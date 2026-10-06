# M06 — Ballot transpose and bit-sliced state

> Encode once and make several later stages operate directly on planes.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** bitplanes, sequence, FSM, compression.
**Prerequisites:** R04 R11. **Evidence:** S03 S08 S10.

## Established substrate [A + H composition; reachability C/P]

Balloting each bit of lane-major categorical values produces word-sized bitplanes. Reconstruction is separate work. The representation redistributes logical parallelism into bits; it does not by itself reduce the information content.

## Appropriation hypothesis

Keep support, sequence categories or small discrete states encoded across multiple transitions. Boolean equality, threshold and neighborhood circuits can avoid repeated scalar loads and branches. Bitplanes can also be the communication payload, especially when later stages need only selected properties.

## Cost and rejection boundary

Both transposes count. One comparison seldom amortizes them; many state steps may. Partial warps require valid masks and cross-word neighbors need explicit carries/boundaries. High-entropy floating states generally need a different representation. Do not re encode at every kernel boundary.

## Next reads

Compositions: C01 C02 C06 C21. Experiments: E01 E13.
