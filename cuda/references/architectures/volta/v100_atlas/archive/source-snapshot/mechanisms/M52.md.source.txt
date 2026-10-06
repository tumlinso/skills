# M52 — Power and thermal budgets as resources

> The best sustained schedule may differ from the maximum instantaneous overlap.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** power, thermal, clocks, adaptation.
**Prerequisites:** R13 R11. **Evidence:** S02 S36.

## Established substrate [D + H policy; reachability C management where permitted]

Compute, memory and interconnect activity share physical module constraints. Clocks/throttling depend onS KU, firmware, cooling and operating limits. Exact coupling is not fully specified here.

## Appropriation hypothesis

Interleave complementary phases or redistribute work away from a throttled critical path. Compare stable throughput and energy per result rather than brief cold peaks. A coarse controller can choose from validated schedules.

## Cost and rejection boundary

Staggering may increase energy or latency. Measure equal useful work at steady temperature and unchanged limits. No voltage/firmware modifications are proposed. Record telemetry averaging, environment and neighbor activity.

## Next reads

Compositions: C33. Experiments: E33 E25.
