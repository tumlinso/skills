# Ampere Kernel Mechanics

Use this route when the first unresolved design choice is fusion, specialization,
or async-staging structure.

## Ampere Bias

- replace manual copy ladders with `cp.async` only when access is regular
- fuse less blindly than Volta when async staging already solves the latency
  problem
- specialize when branch shape or access pattern diverges enough to defeat a
  staged pipeline
