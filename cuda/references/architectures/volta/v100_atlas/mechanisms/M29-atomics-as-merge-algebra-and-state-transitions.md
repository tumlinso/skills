# M29 — Atomics as merge algebra and state transitions

> Arbitration and convergence can be the computation itself.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** atomics, fixed point, ownership, state.
**Prerequisites:** R06 R15. **Evidence:** S03 S30.

## Established substrate [A; reachability C/P]

Atomics supply indivisible supported updates at a scope. Ordering of other data is separate. CAS exposes transition success; OR/min/max can supply useful merge functions. Contention serializes a target.

## Appropriation hypothesis

Use monotone idempotent merges for asynchronous dataflow when duplicates/order can be algebraically harmless. Use CAS for bounded ownership states and atomic reservation for compact outputs. Aggregate locally before crossing a global coordination boundary.

## Cost and rejection boundary

Overwrite and floating addition are not idempotent merges. Prove convergence, termination, fairness and wraparound. A flag does not publish surrounding data without the right ordering. Hot targets can dominate despite high aggregate bandwidth.

## Next reads

Compositions: C04 C24 C25. Experiments: E14 E15.
