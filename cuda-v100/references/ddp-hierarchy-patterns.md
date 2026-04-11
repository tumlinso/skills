# Hierarchy Patterns

## Pair-Local First Reduction

Use this default on the 4x V100 host:

1. local reduction inside `{0,2}`
2. local reduction inside `{1,3}`
3. exchange reduced buffers or leaders across `0<->1` or `2<->3`
4. broadcast within each pair if needed

This is the baseline when gradients or activations are large enough that communication matters.

## When To Prefer It

- all-reduce cost is non-trivial
- communication repeats every step
- pair-local traffic is naturally heavier than cross-pair traffic

## When It Matters Less

- communication volume is tiny
- the workload is dominated by compute and per-step sync is infrequent

## Anti-Pattern

Do not flatten the topology into a symmetric 4-way communication problem just because the framework exposes a flat world size.
