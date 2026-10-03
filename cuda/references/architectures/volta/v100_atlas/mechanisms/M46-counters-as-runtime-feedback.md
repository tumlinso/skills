# M46 — Counters as runtime feedback

> The observation must repay its own cost.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** counters, CUPTI, adaptation.
**Prerequisites:** R12 R10. **Evidence:** S34 S35 S36.

## Established substrate [A/D version-bound + H policy; reachability C/host]

Tracing, counters, sampling and telemetry differ incompatibility/overhead. Some collectors replay work, control clocks or caches, or require privileges. Current docs are not automatic V100support.

## Appropriation hypothesis

At coarse epochs choose between several validated layouts, tiles or push/pull policies. Cheap queue/time information may beat precise counters. Keep a fixed policy control and a bounded decision palette.

## Cost and rejection boundary

Replay measurement may not represent deployment. Noise can trigger oscillation; thermal drift can look like density change. Include instrumentation and switch cost and time-lag. Do not sample the entire machine just to answer a simple local decision.

## Next reads

Compositions: C32 C33. Experiments: E25 E33 E36.
