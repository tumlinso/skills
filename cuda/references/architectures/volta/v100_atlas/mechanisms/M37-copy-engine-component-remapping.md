# M37 — Copy-engine component remapping

> Investigate a restricted format transformer in the movement path.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** DMA, remap, packing, driver.
**Prerequisites:** R09. **Evidence:** S12 S15.

## Established substrate [D; reachability unverified; reachability K]

The Volta copy class exposes component selectors, constants, write suppression and structured addressing. Actual UVM code uses remapping for fills. A complete application route for arbitrary allowed selectors has not been established here.

## Appropriation hypothesis

Copy records with selected field order or constant padding directly into a consumer representation while SMs work. Treat the movement as a limited format stage. A careful descriptor can potentially remove a separate format kernel.

## Cost and rejection boundary

Not arbitrary AoS to SoA, and not a public cudaMemcpy promise. Component width/count, pitch, overlap and lifetime rules need proof. Deep interface setup can cost more than the saved work. Begin with isolated buffers and an owned validated command path.

## Next reads

Compositions: C26. Experiments: E27.
