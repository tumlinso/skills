

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-17: Run real model, harness, topology, quantization, and context bake-off

Task revision: `140`; current project revision is in `todo-status.md`.

## Objective
Using only user-provided assets, evaluate task-level accepted engineering economics across candidate models, quantizations, 8K/16K/32K contexts, Qwen Code and Codex CLI adapters, one-island balanced, two-island throughput, and all-GPU single-wide profiles; select production defaults from accepted-task results rather than generation speed.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `project_exclusive`
- Result: `-`

## Next Action
After the user sets CORE4-MODEL-ASSETS to ready, run the bounded real-task corpus, record frontier-visible inputs/outputs/tool calls and local costs, set the harness/profile decisions, and reach CORE4-HOST-VALIDATED.

## Ownership
- `exclusive`: `local-coding-worker/config/production-profile.toml`
- `exclusive`: `local-coding-worker/evals/host_bakeoff.py`
- `exclusive`: `local-coding-worker/evals/results`
- `exclusive`: `local-coding-worker/evals/tasks`
- `read`: `contracts`
- `read`: `cpp-context-compiler`
- `read`: `cuda`
- `read`: `local-coding-worker`
- `read`: `todo-orchestrator`

## Dependencies
- `task`: `CORE4-16`
- `decision`: `CORE4-MODEL-ASSETS`
<!-- todo-orchestrator:v2-managed:end -->
