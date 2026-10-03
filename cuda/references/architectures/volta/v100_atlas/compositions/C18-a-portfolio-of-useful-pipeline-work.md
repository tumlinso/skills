# C18 — A portfolio of useful pipeline work

> Interleave real subproblems that stress different resources.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** ILP, pipelines, latency hiding.
**Prerequisites:** M16 M08 M11 R14. **Evidence:** S01 S04.

## Construction [H; reachability C/P]


Factor a semantic stage into independently useful components: dense state mixing, integer support maintenance, future address generation, conversion and selected loads. Interleave them while respecting dependencies. Hold multiple independent accumulators only when they correspond to required outputs.

Compare isolated timings, serial composition and interleaved composition. Use resource-demand bounds to explain the result rather than adding all advertised peaks.


## Why it could work

Waiting on one dependency can leave another path able to do required work. Representations that expose independent metadata and payload computation can exploit this without changing the algorithm.

## Full cost and strongest baseline

Issue, register ports, HBM and power are shared. Extra register state can reduce eligible work. A nominally separate instruction family may use the same actual pipe on sm70.

## Falsifier / rejection condition

Reject when “overlap” merely adds work absent from the baseline, or when the shared resource becomes more congested and complete latency grows.

**Experiment:** E02 E03 E39. This composition has not been benchmarked on a V100 here.
