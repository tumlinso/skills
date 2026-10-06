# C31 — Texture interpolation as a nonlinear circuit element

> Tabulate a smooth function and let the sampler supply part of the arithmetic.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** nonlinear, texture, SFU, approximation.
**Prerequisites:** M23 M10 R15. **Evidence:** S30 S03.

## Construction [H; reachability C/P]


Tabulate a smooth scalar function over bounded intervals and use a documented texture filtering path to interpolate. For ideal linear interpolation on interval width h, an error bound is h²·max|f″|/8. Add sample quantization, coordinate/filter precision and output conversion errors to obtain the actual contract.

Use nonuniform regions or explicit exceptional paths around singularities/discontinuities. Multi-dimensional tables can express coupled approximate updates when their size and sampling contract fit.


## Why it could work

The sampler becomes a small lookup-and-interpolation machine, not merely an image accessor. It can replace a longer arithmetic sequence if the table is reused and the error budget permits.

## Full cost and strongest baseline

Compare S FUse ed+refinement, polynomials and cached table+manual interpolation. Include creation/update, traffic and boundary handling. A huge table can replace arithmetic with worse memory pressure.

## Falsifier / rejection condition

Reject if the error bound cannot include real hardware filter behavior, if the function range is unsuitable, or if table traffic/setup exceeds the arithmetic saved.

**Experiment:** E26 E39. This composition has not been benchmarked on a V100 here.
