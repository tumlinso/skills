# M30 — Persistent queues and resident interpreters

> Retain useful state and pay launch cost less often.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** persistent, scheduler, FSM, queues.
**Prerequisites:** R06 R02. **Evidence:** S01 S30 S25.

## Established substrate [A + H composition; reachability C/P]

A kernel can process bounded queued work while resident using normal supported memory/atomic primitives. This is not a special universal task-scheduling instruction.

## Appropriation hypothesis

Keep a finite operator palette, coefficients and support metadata hot. Process compact descriptors, group related tasks and steal work coarsely to balance skew. A task may be a small transform or local state update rather than a whole model layer.

## Cost and rejection boundary

Queue/dispatch/completion overhead must be amortized. Provide bounded capacity, stop/drain and producer progress. Large diverse palettes can inflate instruction footprint and lose optimization. Compare proper batching and graph replay, not an artificially launch-heavy baseline.

## Next reads

Compositions: C25 C34. Experiments: E14 E16 E32.
