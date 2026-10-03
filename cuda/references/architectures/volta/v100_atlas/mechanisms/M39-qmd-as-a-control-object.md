# M39 — QMD as a control object

> Dependent descriptors are a concrete research lead, not a complete hidden runtime.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** QMD, driver, dataflow, launch.
**Prerequisites:** R09 R06. **Evidence:** S13 S27 S40.

## Established substrate [D fields; S broader use; reachability K]

Official Volta QMD fields describe queues, dependent descriptors, releases, resource/cache controls and scheduling-related state. Initialization, ownership, reference counts and many operational rules require additional evidence.

## Appropriation hypothesis

Investigate whether fixed coarse phases can advance through dependency/release machinery with less CPU/SM mediation. Start with two known finite kernels and compare public graph replay. Treat the fields as a research map.

## Cost and rejection boundary

Address units, visibility, cancellation and firmware expectations can invalidate an apparently simple change. Do not patch live CUDA-owned QMDs blindly. A mask field does not automatically mean CUDA SM affinity. No arbitrary self-modifying task graph is claimed.

## Next reads

Compositions: C28. Experiments: E29 E32.
