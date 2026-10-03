# M47 — Special registers and local clocks

> Observe placement and time without treating them as scheduling authority.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** smid, clock, global timer, persistent.
**Prerequisites:** R02 R12. **Evidence:** S03 S04.

## Established substrate [A/E; reachability C/P]

Special registers expose identity/timing with defined limits. smid need not be a dense portable task index; warp i dis not stable application identity. A global timer name is not a guarantee of synchronization between GPUs.

## Appropriation hypothesis

Label resident service instances, gather relative intervals or select local caches. Cross GPU timestamp exchange can estimate offset/drift only after accounting for message asymmetry. Use observations for performance policy, not correctness.

## Cost and rejection boundary

Compiler motion and missing dependencies can invalidate timing. Preemption affects identity assumptions. Do not depend on undocumented time slices or peer time alignment. Record measurement overhead and clock state.

## Next reads

Compositions: C25 C32. Experiments: E02 E16 E19.
