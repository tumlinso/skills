# Addendum: DDP Topology

Use this addendum when the main problem is distributed layout or NCCL communication structure on a 4-GPU Tesla V100 host with diagonal NVLink pairs.

## Workflow

1. Confirm GPU count and rank goal.
   - 2 GPUs or 4 GPUs
   - communication-heavy or mostly pair-local

2. Use the real fast pairs.
   - `0,2`
   - `1,3`

3. Choose the communication shape.
   - pair-local heavy traffic first
   - hierarchical reduction before global exchange
   - one process per GPU by default

4. Place ranks and CPU affinity deliberately.
   - do not let ordinal adjacency hide the real topology

5. Resume the main `cuda-v100` workflow if the bottleneck becomes NCCL protocol choice, peer paths, or low-level communication tuning.

## Support References

- Read `references/ddp-topology-playbook.md` for the preferred 2-GPU and 4-GPU layouts.
- Read `references/ddp-rank-layouts.md` for concrete rank orders, anti-patterns, and CPU-affinity reminders.
- Read `references/ddp-hierarchy-patterns.md` for pair-local-first reduction structures and when to choose them.
- Read `references/ddp-nccl-experiments.md` for the minimal NCCL experiments that are actually worth running on this host.
- Read `references/ddp-benchmark-interpretation.md` when the benchmark data exists but it is still unclear whether the topology or communication shape is the real problem.

## Script

- Use `scripts/emit_rank_layout_env.py` to emit simple environment layouts for the recommended rank pairings.

## Output Requirements

Be explicit about:

- chosen rank grouping
- pair-local versus cross-pair reduction order
- CPU affinity assumptions
- which traffic is allowed to cross pairs and how often
