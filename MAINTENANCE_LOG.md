# Workflow maintenance — 2026-09-06

This is a maintenance record, not a live task queue. The completed Cellerator
Semantic Spine epic exposed these tooling defects and authorized their repair.

- Consolidated the reviewed contract-split reactivation and accepted-integration
  cleanup transactions. Cleanliness, ancestry, terminal run/lane/task state, and
  current integration-gate evidence remain mandatory. Unrelated worktrees remain
  untouched. Repeated recovery preserves the selected producer tip.
- Completion resolves the verified dispatch worktree for producer commit and
  checkpoint hashing. Handoffs separately report authority/main. Integration is
  not implied by completion. Declared artifacts must exist; delivery plans can
  set `result_policy.require_tracked_artifacts` to require Git tracking too.
- Plan validation rejects interface owners whose lane role cannot publish.
  Integrator publication retains ownership and content-hash checks. Explicit task
  selection retains the one-active-lane-per-session guard.
- `cuda` command-gate configuration uses the canonical foreground controller for
  both explicit validation and completion reruns. Resources are controller-owned;
  JSON predicate stdout is preserved, with the controller receipt on stderr.
- Foreground builds use `benchmark.build_argv` before reservation; ignored
  top-level build commands now fail. Toolkit resolution validates compiler and
  sanitizer together. Explicit bad roots fail. `binary_paths` records tested
  binary hashes. Missing requested accelerators cannot become CPU-only success.
- ctxpp no longer injects GCC private intrinsic headers into Clang through either
  command translation path. An SSE compile regression covers both paths.
- Refreshed CUDA guidance and its generated Markdown integrity manifest.

Validation: kernel 392 tests plus the added missing-artifact regression; CUDA 51
tests; ctxpp 60 tests; Project Control 263 tests (one opt-in GPU skip) plus real
MCP lifecycle and V100 gate/completion reruns. The kernel suite must include
`integrations/coding-workflow-mcp` on PYTHONPATH for compatibility/background tests.
The initial omission caused five harness failures; the corrected affected suite
passed. Python 3.13 emits existing unclosed-SQLite ResourceWarnings in fixtures.
