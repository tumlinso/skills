# Blackwell PTX Routing

Use this route only when PTX guidance was explicitly requested.

## Rules

1. Isolate the hot path first.
2. Decide whether the real problem is still family-specific build choice,
   Tensor Core routing, or GB200 deployment shape before reading PTX.
3. Dump only the focused symbol under the Blackwell build target under study.
