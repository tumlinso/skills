# C04 — Warp CAM plus one reservation per equal destination

> Combine match, rank and one atomic into compact grouped output.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** match, compaction, atomics, metadata.
**Prerequisites:** M05 M02 M29 R06. **Evidence:** S03 S10 S30.

## Construction [H; reachability C/P]


Group active lanes by equal destination key. Each group elects its lowest member as leader. The leader reserves popcount(group) output slots once. Broadcast the base to members; each lane writes at base+popcount(group & lower_lane_mask).

The reservation assigns disjoint indexes but does not publish completed payload. Add a separate release/acquire completion protocol when another actor consumes the slots before the kernel/stream boundary. Composite keys require exact equality rather than a los sy hash alone.


## Why it could work

Equal destinations share a local associative group without a persistent hash table. The rank formula is inject i ve within each group. Nonoverlapping atomic reservations make groups disjoint.

## Full cost and strongest baseline

Compare one atomic per lane and established warp aggregation. Sweep destination cardinality and skew. All-distinct groups can make matching overhead pure loss; one huge group can reduce atomics but create leader dependence.

## Falsifier / rejection condition

Reject if group discovery costs more than saved contention, or if the consumer requires an ordering that the proposed slot assignment does not preserve.

**Experiment:** E01 E05 E14 E15. This composition has not been benchmarked on a V100 here.
