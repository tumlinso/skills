# Route: Low-Level ML Boundary

Use this route when the hot path may need to bypass Torch or libtorch entirely for design reasons rather than just kernel reasons.

## Use When

- framework overhead is harming a hot subsystem
- sparse metadata churn or nonstandard layouts do not fit ordinary framework tensors cleanly
- the subsystem may need to own forward and backward directly
- the subsystem may need to own optimizer or update logic directly
- the trainer boundary itself may need to move below Torch or libtorch

## Distinguish The Cases

Use ordinary custom-op planning when:

- the framework still owns the model and optimizer cleanly
- you only need a specific extension boundary
- autograd and optimizer state can stay conventional

Use this route when:

- the hot subsystem is really a low-level ML component, not just an op
- backward state should stay in a custom or sparse layout
- optimizer state should stay fused, blocked, sparse, or otherwise nonstandard
- the trainer loop may need a direct low-level path

## First Move

Read these in order:

1. `references/manual-gradient-system-design.md`
2. `references/optimizer-and-update-design.md` if optimizer ownership is in scope
3. `references/low-level-trainer-loop-design.md` if trainer ownership is in scope
4. `references/sparse-layout-training-boundary.md` for sparse or nonstandard-layout work

Then state:

- what stays framework-managed
- what moves below the framework boundary
- whether ownership covers forward only, forward plus backward, forward plus backward plus optimizer, or most of the trainer
- which layouts or state formats make the low-level path necessary

## Design Rules

- Keep the rest of the model conventional unless the low-level path is clearly justified.
- Treat manual gradients and optimizer ownership as design contracts, not implementation details.
- Prefer a selective low-level subsystem over rewriting the entire model stack without evidence.
- Hand off to `cuda` only after forward, backward, optimizer, and trainer ownership are stable enough to implement.

## Return To Root When

- the low-level ownership boundary is stable and the next uncertainty is implementation rather than model design
