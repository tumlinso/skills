

<!-- todo-orchestrator:v2-managed:start -->
# Todo Status v2 Projection

Project revision: `243`

## Workstreams
- `CORE4-00` | status: done | execution: closed | next: After CORE4-RELEASE-BARRIER opens, verify the release handoff and close the epic.
- `CORE4-19` | status: done | execution: closed | next: Run the single full release gate, inspect only failures, fix regressions narrowly, export the todo snapshot, and publish a compact handoff.
- `CORE4-18` | status: done | execution: closed | next: Implement only policies supported by measured marginal value. Keep defaults conservative and reversible.
- `CORE4-17` | status: done | execution: closed | next: After the user sets CORE4-MODEL-ASSETS to ready, run the bounded real-task corpus, record frontier-visible inputs/outputs/tool calls and local costs, set the harness/profile decisions, and reach CORE4-HOST-VALIDATED.
- `CORE4-17A` | status: done | execution: closed | next: Use /mnt/block/core4-models as canonical cold storage, revise the acquisition destinations, and prove checksum, capacity, and failure-safe cleanup behavior with focused tests. Leave CORE4-MODEL-ASSETS absent.
- `CORE4-16` | status: done | execution: closed | next: Generate an acquisition request containing candidate model files or repositories, quantizations, expected sizes, destinations, checksums when available, and harness prerequisites. If assets are absent, finish this task, then halt and ask the user once.
- `CORE4-15` | status: done | execution: closed | next: Update only public docs and compatibility adapters after the integrated flow works. Run the existing full suites once here, not during every prior task.
- `CORE4-14` | status: done | execution: closed | next: Wire only stable interfaces. Do not bypass them with private imports. Prove read-only, writable, NEEDS_CODEX, stale patch, preemption, accepted patch, and CUDA-trigger cases.
- `CORE4-13` | status: done | execution: closed | next: Add named priority classes and service-owner lifecycle without rewriting todo scheduling. Prove drain, eviction, quiescence, stale-owner recovery, and spare-island correctness behavior with simulated processes.
- `CORE4-07` | status: done | execution: closed | next: Add private bounded telemetry and a fixture evaluation that compares packet layouts at fixed budgets. Do not optimize solely for token reduction.
- `CORE4-11` | status: done | execution: closed | next: Implement adapters against current documented protocols and test them with fakes. Probe installed binaries but do not install or download anything.
- `CORE4-12` | status: done | execution: closed | next: Implement writable mechanics independently of any real model. Use a deterministic fake worker to prove patch and conflict behavior.
- `CORE4-05` | status: done | execution: closed | next: Wire child results into service/context/reporting and publish the stable child-execution contract. Keep normal continue output unchanged when no child result is ready.
- `CORE4-09` | status: done | execution: closed | next: Implement new fact and compatibility modules, preserve raw evidence, and update controller classification without changing existing commands.
- `CORE4-10` | status: done | execution: closed | next: Build the controller and read-only roles first. Do not add writable work, model downloads, recursive agents, or a custom general agent loop.
- `CORE4-04` | status: done | execution: closed | next: Implement the smallest additive schema and CLI surface for child executions, then prove token privilege and recovery behavior.
- `CORE4-06` | status: done | execution: closed | next: Implement additive inspect/packet commands without weakening fast where/route/status behavior or source-authority guarantees.
- `CORE4-08` | status: done | execution: closed | next: Implement registry validation and changed-code matching in new modules, then add thin controller commands without guessing among ambiguous production benchmarks.
- `CORE4-03` | status: done | execution: closed | next: Add schemas and thin adapters around current background primitives. Do not redesign the scheduler or move skill-specific semantics into the facade.
- `CORE4-02A` | status: done | execution: closed | next: Inspect the targeted refresh implementation, failing test, and existing ctxpp retrieval/freshness contract; change only the test if lexical-only freshness is contract-valid, otherwise repair the implementation; run the focused test and full ctxpp suite, then freeze CORE4-BASELINE-FROZEN.
- `CORE4-02` | status: done | execution: closed | next: After CORE4-02A resolves the ctxpp baseline contract and freezes CORE4-BASELINE-FROZEN, resume only to verify and close the baseline task.
- `CORE4-01` | status: done | execution: closed | next: Bootstrap complete; implementation begins at CORE4-02.
<!-- todo-orchestrator:v2-managed:end -->
