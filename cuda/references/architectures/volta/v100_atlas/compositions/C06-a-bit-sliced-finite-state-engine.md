# C06 — A bit-sliced finite-state engine

> Compile small state transitions into gates rather than per-object branches.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** FSM, state, Boolean, branch elimination.
**Prerequisites:** M01 M06 M07 M14. **Evidence:** S03 S08.

## Construction [H; reachability C/P]


Encode a small state by q0..qk−1 planes. For a two-bit saturating counter with increment plane u:

```
s0=q0^u; carry=q0&u
s1=q1^carry; overflow=q1&carry
out0=s0|overflow; out1=s1|overflow
```

This maps0→1→2→3→3 wherever u is set and leaves other instances unchanged. More general finite transitions can be minimized into shared Boolean subexpressions. Keep event and validity planes alongside state.


## Why it could work

The rule is a finite truth function. Its circuit evaluates many instances with identical control and no divergent per-instance switch. State can stay in registers across repeated steps.

## Full cost and strongest baseline

Compare packed saturating intrinsics and conventional branch/predicate code. Circuit size grows with state/rule complexity; a huge truth table is not automatically cheap. Count event-plane generation and cross-instance information exchange.

## Falsifier / rejection condition

Reject when the state is genuinely high-dimensional continuous data, when rules vary independently per object, or when code/register growth exceeds the eliminated control work.

**Experiment:** E01 E13 E39. This composition has not been benchmarked on a V100 here.
