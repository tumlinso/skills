

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-11: Implement model-server and coding-harness adapters

Task revision: `23`; current project revision is in `todo-status.md`.

## Objective
Add replaceable adapters for llama.cpp serving and existing coding harnesses, initially Qwen Code and Codex CLI, with inspect/start/health/run/cancel/drain/evict/usage APIs, disposable task contexts, fake servers, and no asset installation.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `parallel_safe`
- Result: `-`

## Next Action
Implement adapters against current documented protocols and test them with fakes. Probe installed binaries but do not install or download anything.

## Ownership
- `exclusive`: `local-coding-worker/local_worker/harnesses`
- `exclusive`: `local-coding-worker/local_worker/servers`
- `exclusive`: `local-coding-worker/local_worker/service.py`
- `exclusive`: `local-coding-worker/references/adapter-contract.md`
- `exclusive`: `local-coding-worker/tests/test_adapters.py`
- `read`: `local-coding-worker/local_worker/controller.py`
- `read`: `todo-orchestrator/todo_orchestrator/runtime`

## Dependencies
- `checkpoint`: `CORE4-LOCAL-READONLY-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
