# M32 — Cooperative grids and historical multidevice launch

> Keep forgotten mechanisms in view, but retain their admission and version constraints.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** cooperative, grid, multi GPU.
**Prerequisites:** R06 R10. **Evidence:** S30 S03.

## Established substrate [A conditional; reachability C]

Cooperative grid synchronization depends on supported launch/capacity rules. Historical multi-device cooperative launch has additional requirements and lifecycle limits. Ordinary kernels do not inherit these guarantees.

## Appropriation hypothesis

Use a cooperative grid as a phase machine when global synchronization and resident resources fit. Study the old multi-device mechanism as a possible primitive and evidence of runtime design, not as fused hardware scheduling.

## Cost and rejection boundary

Check installed APIs and per-device flags. Deprecated is not necessarily absent, but not automatically durable. Oversized grids or unsupported interactions invalidate assumptions. No shared cache or cross GPU CTA follows from coordinated launch.

## Next reads

Compositions: C25 C39. Experiments: E16 E32 E36.
