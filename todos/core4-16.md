

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-16: Prepare exact host acquisition and bake-off manifest

Task revision: `163`; current project revision is in `todo-status.md`.

## Objective
Inspect the actual machine, installed CUDA 12.x toolchains, llama.cpp/Qwen Code/Codex CLI availability, free storage, GPU topology, RAM, and existing model cache; emit the smallest exact user action needed for real model evaluation without downloading or installing anything.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `validated`

## Next Action
Generate an acquisition request containing candidate model files or repositories, quantizations, expected sizes, destinations, checksums when available, and harness prerequisites. If assets are absent, finish this task, then halt and ask the user once.

## Ownership
- `exclusive`: `local-coding-worker/config/host-profile.example.toml`
- `exclusive`: `local-coding-worker/evals/acquisition_request.json`
- `exclusive`: `local-coding-worker/scripts/inspect_host.py`
- `exclusive`: `local-coding-worker/tests/test_host_manifest.py`
- `forbidden`: `models`
- `forbidden`: `weights`
- `read`: `cuda/scripts/cuda_controller.py`
- `read`: `local-coding-worker/local_worker/harnesses`
- `read`: `local-coding-worker/local_worker/servers`

## Dependencies
- `checkpoint`: `CORE4-SOFTWARE-READY`
<!-- todo-orchestrator:v2-managed:end -->
