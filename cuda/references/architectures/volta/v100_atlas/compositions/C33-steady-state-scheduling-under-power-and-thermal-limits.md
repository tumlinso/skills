# C33 — Steady-state scheduling under power and thermal limits

> Optimize useful sustained work rather than cold instantaneous utilization.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** power, thermal, scheduling.
**Prerequisites:** M52 M46 R11 R13. **Evidence:** S02 S36.

## Construction [H; reachability C/P]


Measure several equal-work schedules: maximal overlap, phase interleaving and topology redistribution. Keep allowed power limits unchanged. Observe stable clocks, temperature, throughput and energy per result after thermal settling.

A coarse policy may choose a different schedule when one module or resource remains throttled. This is software work placement, not voltage/firmware modification.


## Why it could work

Compute, memory and fabric compete within physical budgets. A schedule with less instantaneous overlap could sustain a better useful rate if it avoids a persistent shared limit; the opposite is equally possible.

## Full cost and strongest baseline

Compare at identical outputs and environment. Longer wall time can increase energy even at lower power. Sensor averaging and neighbor activity can hide short phases. Cold startup comparisons are inadequate.

## Falsifier / rejection condition

Reject if the effect disappears at steady state, if it merely reduces work/accuracy, or if management overhead outweighs any sustained gain.

**Experiment:** E33 E25. This composition has not been benchmarked on a V100 here.
