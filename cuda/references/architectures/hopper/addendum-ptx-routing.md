# Hopper PTX Routing

Use this route only when PTX guidance was explicitly requested.

## Rules

1. Isolate the hot path first.
2. Decide whether the real problem is still TMA, cluster structure, or Tensor
   Core routing before reading PTX.
3. Dump only the focused symbol under `sm_90`.
