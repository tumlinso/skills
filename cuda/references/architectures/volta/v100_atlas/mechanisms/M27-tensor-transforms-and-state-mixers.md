# M27 — Tensor transforms and state mixers

> Fixed coefficient matrices can be configurable algebraic circuit elements.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** FFT, transforms, dynamics, tensor.
**Prerequisites:** R05 R15. **Evidence:** S03 S19 S21 S24.

## Established substrate [A/E + H composition; reachability P/C]

Small matrix products implement fixed linear transformations. Original work demonstrates tensor-based reductions, precision expansion and FFT-related transforms, with workload and format limits.

## Appropriation hypothesis

Encode local stencil mixtures, basis changes, Haar/Hadamard-like mixing or real/imaginary butterfly components. Reuse coefficients and fragment-native state across steps. The four native subproblems can carry unrelated transforms.

## Cost and rejection boundary

Structured zeros/ones may be cheaper as add/shuffle networks. A nonlinear transition needs lifting, piecewise selection or another primitive; putting it in a matrix does not make it linear. Bound range growth and include packing/coefficient load/extraction.

## Next reads

Compositions: C10 C13 C15. Experiments: E12 E39.
