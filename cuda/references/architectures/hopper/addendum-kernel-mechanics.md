# Hopper Kernel Mechanics

Use this route when the first unresolved design choice is TMA, clusters,
distributed shared memory, fusion, or specialization.

## Hopper Bias

- use TMA for large regular tensor movement, not for irregular glue
- cluster only when blocks truly cooperate on shared state
- avoid carrying Ampere-style staging complexity forward when TMA or clusters
  give a cleaner ownership model
