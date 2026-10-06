# C13 — Fixed transforms as configurable tensor circuits

> Use small basis changes, stencils or butterfly components as reusable coefficient banks.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** FFT, Hadamard, stencil, transform.
**Prerequisites:** M27 M25 R05 R15. **Evidence:** S24 S03 S23.

## Construction [H; reachability C/P]


Represent a local transform by a fixed small coefficient matrix. Hadamard-style ±1 mixing, small stencil neighborhoods, real-valued pieces of complex butterflies and local dynamical basis changes are candidates. Fit supported native shapes; compose phases while preserving native register ownership.

For a nonlinear operator, identify the true linear substep or a justified lifted representation. Do not claim that an arbitrary nonlinear function becomes a matrix merely by naming its state differently.


## Why it could work

The tensor primitive implements a reusable bilinear circuit. Fixed coefficients can be reused across many states or iterations. Original tensor FFT work demonstrates that non-neural transforms are a real direction, not just metaphor.

## Full cost and strongest baseline

Compare sparse add/subtract/shuffle networks. A Hadamard matrix has special structure a dense product does not exploit. Include coefficient preparation, normalization, range growth and complex-layout costs.

## Falsifier / rejection condition

Reject when the structured SIMT circuit has much less useful work, or when precision/error grows unacceptably across repeated transforms.

**Experiment:** E12 E10 E39. This composition has not been benchmarked on a V100 here.
