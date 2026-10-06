# M13 — Operand reuse and dependency control

> The short-lived operand path is a resource distinct from register capacity.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** reuse, scoreboard, manual scheduling.
**Prerequisites:** R02 R10. **Evidence:** S04 S05 S11.

## Established substrate [E/R; reachability B]

Volta machine code carries dependency/stall/yield/reuse information invisible in ordinary CUDA. These fields influence when operands can be consumed and when a variable-latency result is safe.

## Appropriation hypothesis

Keep repeated operands close in the instruction stream and interleave independent work while a dependency matures. A small algebraic change can improve the operand stream even with the same FLOP count. Reuse-aware layouts can avoid rereading common coefficients.

## Cost and rejection boundary

These controls are correctness machinery. Removing waits because one run passed can fail at another memory latency. Preserve original cubins and exact transformations. Extra ILP that extends many live values can spill. Measure complete kernels after isolated schedules.

## Next reads

Compositions: C17 C18. Experiments: E04 E30.
