# Manual Gradient System Design

Use this reference when a hot subsystem may need to own backward logic directly.

## When Manual Backward Is Worth Considering

- framework autograd state is too large for the real hot path
- saved tensors would require repeated layout repair or metadata expansion
- sparse or blocked layouts should remain in their native form through backward
- the backward path is structurally different enough that framework decomposition adds avoidable overhead
- recomputation is cheaper than saving framework-shaped state

## Do Not Use This Path By Default

Reject manual backward when:

- the subsystem is not actually hot
- ordinary autograd already expresses the layout cleanly
- the real problem is still model-family choice or kernel implementation quality

## Required Contract

State these before implementation starts:

- forward inputs and outputs
- saved state that must survive into backward
- which state can be recomputed instead of saved
- backward inputs and outputs
- gradient accumulation policy
- dtype and layout assumptions for activations, parameters, and gradients
- which values are differentiable, fixed, or intentionally nondifferentiable

## Recompute Versus Save

Prefer recomputation when:

- saved state is large or layout-hostile
- sparse metadata is expensive to materialize every step
- the backward math can cheaply reconstruct the needed intermediates

Prefer saving when:

- the backward path would otherwise replay expensive irregular work
- recomputation would amplify memory traffic or synchronization too much

## Sparse And Nonstandard Layout Notes

- Keep sparse gradients sparse only when the update path can actually consume them efficiently.
- Do not promise sparse backward semantics if the optimizer path will densify immediately.
- Make layout ownership explicit at the design level so `cuda-v100` can implement the correct state contract later.

## Output Checklist

State:

- why framework autograd is insufficient
- what backward owns directly
- what is saved versus recomputed
- how gradient layout is represented
- what still remains framework-managed
