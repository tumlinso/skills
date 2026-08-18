# Ampere PTX Routing

Use this route only when PTX guidance was explicitly requested.

## Rules

1. Isolate the hot path first.
2. Decide whether the real problem is still staging, Tensor Core routing, or
   decomposition before reading PTX.
3. Dump only the focused symbol under `sm_80`.
