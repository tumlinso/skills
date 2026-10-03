# M51 — Faults, reset and RAS

> Long-lived computation needs a failure model as well as a fast path.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** faults, RAS, ECC, reset.
**Prerequisites:** R13 R08. **Evidence:** S02 S28 S36.

## Established substrate [D; reachability C telemetry; K recovery]

ECC, replay, retirement and link errors have different boundaries. The Volta fault buffer implementation contains an ordered overflow-clear workaround. Management reset can require linked older GPU groups.

## Appropriation hypothesis

Use health state to reject contaminated measurements and trigger coarse fallback outside hot loops. Checkpoint or use idempotent work boundaries so restart/replay has defined semantics.

## Cost and rejection boundary

Do not turn overflow into an intentional queue, disable protection for uncorroborated speed, or reset as routine benchmark setup. API recovery does not guarantee every engine is independently resettable. Validate outputs after faults.

## Next reads

Compositions: C24 C39. Experiments: E24 E34.
