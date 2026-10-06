# M23 — Constant and texture paths as function interfaces

> Specialized lookup behavior can embody a small operator.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** constant, texture, lookup, interpolation.
**Prerequisites:** R03 R15. **Evidence:** S03 S30.

## Established substrate [A; reachability C/P]

Constant broadcast benefits appropriate common addresses; divergent addresses change the cost. Texture sampling has explicit coordinates, formats and filtering behavior. Neither is a universal faster global load.

## Appropriation hypothesis

Store shared transition coefficients in a broadcast-friendly form. Use a tabulated smooth function plus interpolation as a nonlinear circuit element. Spatial lookup can sometimes suit the specialized cache/address machinery better than general pointer traversal.

## Cost and rejection boundary

Filtering precision, boundaries, conversion and update visibility are part of the contract. Random divergent constant lookups may serialize. Compare cached global, shared, manual interpolation andS FU routes at equal error tolerance.

## Next reads

Compositions: C31. Experiments: E26 E07.
