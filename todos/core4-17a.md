

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-17A: Prepare external cold-storage staging for the host bake-off

Task revision: `170`; current project revision is in `todo-status.md`.

## Objective
Add a configuration-driven, model-independent staging utility that copies one user-provided candidate from canonical cold storage to SSD, verifies SHA256 before execution, preserves source metadata, and removes staged files after success, failure, or interruption without downloading or installing assets.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `implemented`

## Next Action
Use /mnt/block/core4-models as canonical cold storage, revise the acquisition destinations, and prove checksum, capacity, and failure-safe cleanup behavior with focused tests. Leave CORE4-MODEL-ASSETS absent.

## Ownership
- `exclusive`: `local-coding-worker/config/host-profile.example.toml`
- `exclusive`: `local-coding-worker/evals/acquisition_request.json`
- `exclusive`: `local-coding-worker/evals/model_staging.py`
- `exclusive`: `local-coding-worker/tests/test_model_staging.py`
- `read`: `local-coding-worker/local_worker/harnesses`
- `read`: `local-coding-worker/local_worker/servers`
- `read`: `local-coding-worker/scripts/inspect_host.py`

## Dependencies
- `task`: `CORE4-16`
<!-- todo-orchestrator:v2-managed:end -->
