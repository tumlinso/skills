# Low-Level Trainer Loop Design

Use this reference when the training loop itself may need to move partly or mostly below Torch or libtorch.

## Use When

- one subsystem owns forward, backward, and updates as a coherent low-level path
- trainer overhead is dominated by repeated boundary crossings
- the model needs nonstandard ordering of reduction, update, masking, or remapping
- sparse or layout-sensitive state should not cross the framework boundary every step

## Scope Choices

Choose the narrowest design that works:

- low-level hot subsystem wrapped by a conventional trainer
- low-level subsystem plus owned optimizer step
- mostly low-level trainer with only thin high-level orchestration

## Required Design Decisions

Specify:

- parameter and state lifetime
- loss evaluation boundary
- backward and update ordering
- gradient synchronization boundary
- checkpoint ownership
- adapter boundaries between framework-managed and low-level-managed components

## Design Rules

- Keep conversions out of the per-step hot path.
- Avoid a mixed boundary that forces layout repair on every forward or backward call.
- Keep the non-hot path simple; complexity belongs only where it buys real performance or layout control.
- Reject a framework-free trainer if the expected savings are small relative to the engineering burden.

## Output Checklist

State:

- what part of the trainer stays high-level
- what part becomes low-level
- how parameters, losses, gradients, and updates cross the boundary
- why the chosen scope is smaller than a full rewrite, or why a broader rewrite is justified
