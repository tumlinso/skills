# PCU-V1 validation harnesses

`pcu_harness.py` provides deterministic primitives used by the later PCU
integration and validation tasks. Its CLI is fail-closed and path-explicit.

- `verify-release` validates the release manifest and its parent-source tree.
- `verify-independent-clone` creates only a new `git clone --no-local` target
  and proves the source sentinel and Git common directory are independent.
- `candidate-plan` emits, but does not execute, an isolated virtual-environment
  build plan containing both local distributions.
- `atomic-swap` runs explicit argv arrays and executes every supplied rollback
  command if forward installation or verification fails.

The Python API also validates release locks and gitlinks, and rehearses
dry-run/apply/idempotent-reapply/remove exclusively inside an independent clone.
No command discovers or selects a downstream repository, live service, MCP
registration, tunnel, or installed environment.
