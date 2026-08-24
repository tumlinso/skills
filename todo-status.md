

<!-- todo-orchestrator:v2-managed:start -->
# Todo Status v2 Projection

Project revision: `78`

## Workstreams
- `C4P-00` | status: planned | execution: inactive | next: Close only after C4P-24 is validated.
- `C4P-24` | status: planned | execution: ready | next: After this task and C4P-00 are completed, archive/remove the active ledger outside todo, run the final static tracked-layout check, commit, and fast-forward push core4-bootstrap. Do not merge main.
- `C4P-23` | status: planned | execution: ready | next: Commit and push the coherent release candidate on core4-bootstrap, then prepare final ledger archival.
- `C4P-22` | status: planned | execution: ready | next: Verify the eventual tracked layout contains only the four skills, AGENTS.md, .gitignore, and optional self-contained .github.
- `C4P-21` | status: planned | execution: ready | next: Run this full gate once. Repair only actual regressions and rerun the affected suite before one final aggregate run.
- `C4P-20` | status: planned | execution: ready | next: Do not promote from keyword matching. Use objective gates and compact accepted-task comparisons; retain raw artifacts only in the Git common directory.
- `C4P-19` | status: planned | execution: ready | next: Update minimal SKILL.md routing and versioned policy without exposing server operation details to Codex.
- `C4P-18` | status: planned | execution: ready | next: Use integer acceptance counts and report unavailable candidates as not_evaluated, not failed.
- `C4P-17` | status: planned | execution: ready | next: Repair implementation defects revealed by these scenarios, then rerun only the failed scenario set.
- `C4P-16` | status: planned | execution: ready | next: Use the smallest task set that proves the path; inspect raw logs only on failure.
- `C4P-15` | status: planned | execution: ready | next: Do not evaluate model quality yet; establish reliable service operation and record compact host evidence.
- `C4P-14` | status: done | execution: closed | next: If the active candidate is not READY, stop after emitting the exact request. Do not download, install, copy, or continue to C4P-15.
- `C4P-13` | status: done | execution: closed | next: Fix only failures attributable to the extension; do not start a model or GPU benchmark.
- `C4P-12` | status: done | execution: closed | next: Test no-match, one-match, ambiguous, contaminated, preempted, and accepted-patch scenarios without real GPU timing.
- `C4P-11` | status: done | execution: closed | next: Use simulated model output first, then leave the same normalized path ready for the real host test.
- `C4P-10` | status: done | execution: closed | next: Prove the full production path with fake server and harness adapters before using real weights.
- `C4P-08` | status: done | execution: closed | next: Use a fake llama-server fixture for focused tests; do not require real weights yet.
- `C4P-04` | status: done | execution: closed | next: Implement against the existing coordinator rather than creating a second scheduler.
- `C4P-03` | status: done | execution: closed | next: Implement the migration and lifecycle first, then focused child, recovery, guard-path, and compatibility tests.
- `C4P-05` | status: done | execution: closed | next: Fix the evidence-ordering defect first and prove contaminated runs create no durable fact or escalation.
- `C4P-06` | status: done | execution: closed | next: Start with schema and source-identity compatibility, then packet ranking and focused worker-oriented fixtures.
- `C4P-07` | status: done | execution: closed | next: Implement software and fake-file tests only. Do not copy or download a real model in this task.
- `C4P-09` | status: done | execution: closed | next: Inspect the installed Qwen CLI help once, then implement a version adapter. Do not browse or launch a model.
- `C4P-02` | status: done | execution: closed | next: Run the baseline section once; do not modify public semantics in this task.
- `C4P-01` | status: done | execution: closed | next: After plan application, record archive paths and complete this task, then continue to C4P-02.
<!-- todo-orchestrator:v2-managed:end -->
