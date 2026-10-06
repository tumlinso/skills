# Multi-GPU Topology And DDP

Use this guide when rank placement, collectives, or NCCL communication may be topology-bound. The native host's recorded profile has fast pairs `0,2` and `1,3`, but indices are observations, not authority: rediscover device UUIDs and topology at runtime before placing processes or selecting devices. Never assume ordinal adjacency or treat a script-emitted mapping as admission.

The examples below use the native host's two- and four-GPU layouts. For other
deployments, derive groups from the observed fabric; use [GB200 NVL72](gb200-nvl72.md)
for that rack's deployment constraints.

## Workflow

1. Confirm GPU count and rank goal.
   - 2 GPUs or 4 GPUs
   - communication-heavy or mostly pair-local

2. After runtime discovery, compare the measured fabric to the recorded native profile. If it matches, test these pairs:
   - `0,2`
   - `1,3`

3. Choose the communication shape.
   - pair-local heavy traffic first
   - hierarchical reduction before global exchange
   - one process per GPU by default

4. Place ranks and CPU affinity deliberately.
   - do not let ordinal adjacency hide the real topology

5. For correctness or timing on the shared host, follow [host execution](../execution/host-execution.md) first. The controller selects runtime devices and enforces admission; rank-layout helpers express a candidate ordering inside the admitted run.

Use [topology patterns](ddp-topology-playbook.md) for 2-GPU and 4-GPU decompositions; [rank layouts](ddp-rank-layouts.md) for logical-to-physical mapping and CPU affinity; [hierarchy patterns](ddp-hierarchy-patterns.md) when reductions cross pairs; and [NCCL experiments](ddp-nccl-experiments.md) only after defaults and observed paths are understood. If measurements disagree, [interpretation rules](ddp-benchmark-interpretation.md) separate fabric effects from rank, CPU, and message-size effects.

## Script

- Use `scripts/emit_rank_layout_env.py` to emit simple environment layouts for the recommended rank pairings.

## Report

Be explicit about:

- chosen rank grouping
- pair-local versus cross-pair reduction order
- CPU affinity assumptions
- which traffic is allowed to cross pairs and how often
