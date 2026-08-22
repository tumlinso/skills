

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-18: Tune reviewer, double-solve, context, and delegation policy

Task revision: `23`; current project revision is in `todo-status.md`.

## Objective
Use the host bake-off evidence to enable reviewer or independent-double-solve only where it lowers frontier rework, tune delegation eligibility and context budgets by task class, set hot-idle and preemption policies, and preserve explicit NEEDS_CODEX behavior.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `serial`
- Result: `-`

## Next Action
Implement only policies supported by measured marginal value. Keep defaults conservative and reversible.

## Ownership
- `exclusive`: `local-coding-worker/config/production-profile.toml`
- `exclusive`: `local-coding-worker/evals/results/policy-report.json`
- `exclusive`: `local-coding-worker/local_worker/policy.py`
- `exclusive`: `local-coding-worker/local_worker/reviewer.py`
- `exclusive`: `local-coding-worker/local_worker/telemetry.py`
- `exclusive`: `local-coding-worker/tests/test_policy.py`
- `read`: `cpp-context-compiler/evals`
- `read`: `local-coding-worker/evals/results/host-bakeoff.json`

## Dependencies
- `checkpoint`: `CORE4-HOST-VALIDATED`
<!-- todo-orchestrator:v2-managed:end -->
