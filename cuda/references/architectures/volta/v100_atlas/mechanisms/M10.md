# M10 — S F Us and interpolation as alternate arithmetic

> Use a different unit only with a deliberate error budget.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** SFU, approximation, nonlinear.
**Prerequisites:** R02 R15. **Evidence:** S01 S03 S04 S30.

## Established substrate [A/E; reachability C/P]

Special functions and texture interpolation have distinct precision, format and throughput contracts. A fast approximate primitive is not equivalent to a full library function. Historical latency is not a full concurrency model.

## Appropriation hypothesis

Build a nonlinear update from an approximate reciprocal/rsqrt seed and a correction. A table plus texture interpolation can embody a piecewise function. Choose the route that reduces the occupied bottleneck rather than merely the scalar operation count.

## Cost and rejection boundary

Singularities, large exponent ranges, subnormals and clipping boundaries need analysis. Include table setup, traffic and conversion. Compiler fast-math flags can change the contract rather than only the schedule. An unbounded approximation is not a safe exact decision filter.

## Next reads

Compositions: C31 C18. Experiments: E26 E03.
