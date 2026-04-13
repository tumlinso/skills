# Optimizer And Update Design

Use this reference when the subsystem may need to bypass Torch optimizers or own its update logic directly.

## When Low-Level Optimizer Ownership Is Justified

- parameter layout is sparse, blocked, or custom-packed enough that framework optimizers pay repeated conversion cost
- optimizer state should share the subsystem's native layout
- fused or custom update rules are central to the hot path
- sparse updates or masked updates are a first-order part of the algorithm
- the framework boundary would force unnecessary materialization or synchronization

## Keep Framework Optimizers When

- parameters already live in ordinary dense tensors
- the update rule is standard and not meaningfully hot
- the real limiter is forward or backward, not the optimizer step

## Required Contract

Specify:

- parameter ownership
- optimizer state ownership
- update rule and schedule
- mixed-precision or master-weight ownership
- gradient accumulation and zeroing policy
- checkpoint and serialization boundary
- distributed implications for reductions, sharding, or replicated state

## Ownership Levels

Choose one:

- framework-managed optimizer with a low-level forward path
- low-level optimizer for one subsystem while the rest of training stays framework-managed
- framework-free optimizer ownership for most of the trainer

## Design Warnings

- Do not take optimizer ownership just to mirror an implementation preference.
- Reject low-level optimizer work if layout mismatch is not actually dominant.
- Treat update-state layout as part of the model design, not a late implementation detail.

## Output Checklist

State:

- why framework optimizers are inadequate or acceptable
- which parameters live in the low-level path
- what optimizer state is owned directly
- how updates, checkpointing, and mixed precision interact
