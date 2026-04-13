# Sparse Layout Training Boundary

Use this reference when sparse formats or nonstandard layouts are the main reason to consider a low-level ML subsystem.

## Typical Triggers

- sparse aggregation with heavy metadata churn
- blocked sparse or custom-packed activations
- irregular sparse updates or masked updates
- backward state that should remain CSR, CSC, COO, blocked, or custom packed
- optimizer state that should share the same sparse or blocked layout

## When Layout Justifies Framework Bypass

The low-level path is justified when:

- the framework keeps forcing expensive densification, reindexing, or layout repair
- forward, backward, or optimizer state should stay in one native sparse layout
- the boundary between sparse and dense work is clear and stable
- the low-level path can keep metadata movement below the framework boundary

The low-level path is not justified when:

- layout churn is minor
- the real bottleneck is elsewhere
- the framework can already keep the critical state in an adequate form

## Design Questions

State:

- which layout dominates the hot path
- where sparse-to-dense boundaries occur
- whether backward should preserve sparse structure
- whether optimizer state should stay sparse, blocked, or packed
- whether the framework should only see reduced summaries, embeddings, losses, or checkpoint shells

## Common Good Outcomes

- keep a sparse or blocked subsystem low-level while the rest of the model stays conventional
- keep backward and optimizer state inside the same layout-aware subsystem
- expose only the minimum dense interface needed for loss computation or downstream heads

## Common Bad Outcomes

- keeping the framework in the loop for every sparse metadata transform
- designing a low-level path that still converts layouts every step
- bypassing the framework before proving that layout mismatch is the actual cost center

## Handoff Rule

Once the layout boundary and ownership rules are stable, use `cuda-v100` for implementation, kernel decomposition, profiling, and V100-specific optimization.
