# C10 — Four tiny linear machines in one MMA warp

> Use the real native groups for local operators instead of pretending every row must be a batch example.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** HMMA, small matrices, state, graph.
**Prerequisites:** M24 M25 R05 R15. **Evidence:** S03 S22 S23.

## Construction [H; reachability C/P]


Assign one 8×8×4 product to each documented lane group. Fill A/B with actual semantic dimensions: local actors×latent components, transition coefficients, basis components or four unrelated graph patches. All32 required lanes execute the same instruction.

A dimension shorter than four can be padded. A longer contraction needs several instructions and a correct accumulation layout. Write the operator equation before assigning data; reshaping a vector into a square does not manufacture a useful dense relation.


## Why it could work

The product is bilinear and indifferent to whether its dimensions represent tokens, batches, genes or hidden-state factors. Independent native groups permit small structures without forcing unrelated values to mix.

## Full cost and strongest baseline

Compare scalar/register algebra and batched library paths. Track useful products versus padding, coefficient reuse, fragment loading and extraction. A fixed low-rank factorization can help only when it preserves the intended operator and saves enough work.

## Falsifier / rejection condition

Reject when the operation is mostly routing/addition, when inter-group exchange dominates, or when precision/range cannot support the semantic state.

**Experiment:** E09 E10 E12 E39. This composition has not been benchmarked on a V100 here.
