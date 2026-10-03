# M02 — Mask rank/select as routing

> Membership, local index and next destination can live in the same word.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** support, rank, select, compaction.
**Prerequisites:** R04 R06. **Evidence:** S03 S08 S10.

## Established substrate [A; reachability C/P]

Ballot collects lane predicates. Population count below a lane gives its rank; bit searches select members. __fns has a specific base/offset/sentinel contract, not just the intuitive name “find nth bit.” Its sm70 cost must be inspected.

## Appropriation hypothesis

Use a support word as a compressed dispatch table. Rank assigns compact output positions; select picks a source; shuffle retrieves payload. Preserve masks between stages instead of expanding them to index arrays. Empty-set tests can suppress a larger operation, not merely one branch.

## Cost and rejection boundary

Word-width shifts and no-result sentinels need explicit handling. The selected source must be a participant. Sparse enumeration and dense fixed networks have different crossovers. POPC is not assumed to share ADD latency; a clever mask pipeline can still become a dependent popcount chain.

## Next reads

Compositions: C04 C05 C35 C37. Experiments: E01 E05.
