# Overlap Rules

## CPU Vs GPU Preprocessing

Keep work on CPU when:

- it is light
- it does not fragment the transfer path
- it avoids large extra device-side passes

Move work to GPU when:

- it can be fused with the steady-state path
- host-side assembly is the limiter
- it removes round-trips or repeated host staging

## Transfer Rules

- pin memory for real transfer buffers
- batch many tiny transfers into larger transfers
- avoid host-visible intermediate layouts if the GPU can consume a better format directly

## NUMA Rule

Stage data near the target GPU’s CPU locality when possible. The diagonal NVLink topology does not remove host-side NUMA effects.
