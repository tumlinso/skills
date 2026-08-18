# Topology Playbook

## Real Fast Pairs

- fast pair A: `0<->2`
- fast pair B: `1<->3`

Acceptable leader exchange:

- `0<->1`
- `2<->3`

Worst paths:

- `0<->3`
- `1<->2`

## Preferred 2-GPU Choices

Use:

- `0,2`
- `1,3`

Do not default to `0,1` or `2,3` just because the ordinals are adjacent.

## Preferred 4-GPU Decomposition

Use:

- group A = `{0,2}`
- group B = `{1,3}`

Then:

- reduce inside each group first
- exchange leaders or reduced summaries second
- broadcast back inside the pair if needed

Leader choices:

- prefer `0<->1` for one inter-group exchange path
- prefer `2<->3` for the other
- avoid cross-group exchange that relies on `0<->3` or `1<->2`

## Good Patterns

- pair-local tensor-parallel style traffic
- hierarchical all-reduce
- pair-local replicas with coarse-grained synchronization across pairs

## Bad Patterns

- hot steady-state traffic over `SYS`
- full 4-way communication patterns that ignore the diagonal fast pairs
- rank layouts that make the good pairs invisible to the launcher or framework
- one-process multi-GPU launch strategies that destroy CPU locality for communication-heavy work

## Decision Table

| Situation | Preferred pattern |
|---|---|
| 2-GPU communication-heavy training | `0,2` or `1,3` only |
| 4-GPU all-reduce heavy training | pair-local first, cross-pair leaders second |
| model fits in 2 GPUs | pair-local replicas before 4-way coupling |
| communication is light, compute is dominant | looser grouping can be tolerated, but keep rank order topology-aware |
