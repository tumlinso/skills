---
name: local-coding-worker
description: Delegate bounded, todo-authorized read-only or scoped writable coding work to a local backend using ctxpp packets and isolated source state. Use only when an active parent todo claim authorizes a child execution. Never use it for architecture, task ownership, commits, pushes, or recursive agents.
---

# Local Coding Worker

## Repository workflow

For substantial repository work, ALWAYS use `coding-workflow` first when it is
available. Claim or resume the authoritative task through `coding-workflow`
before using this skill for bounded delegation. Do not directly claim todo work
or begin repository mutations first. Use lower-level skill CLIs directly only
when `coding-workflow` is unavailable, explicitly out of scope, or itself being
debugged.

Use this skill only from an active todo parent claim. The parent retains task,
gate, acceptance, commit, and push authority.

Delegate through the single public command and consume its compact result:

```bash
python <skill-dir>/scripts/local_worker.py delegate \
  --claim-token <parent-claim-token> --mode <readonly|writable> --wait --json
```

Omit `--wait` to launch explicitly authorized independent work without blocking,
then collect it by execution ID:

```bash
launch=$(python <skill-dir>/scripts/local_worker.py delegate \
  --claim-token <parent-claim-token> --mode <readonly|writable> --json)
python <skill-dir>/scripts/local_worker.py delegate \
  --collect <execution-id-from-launch> --wait --json
```

Launching twice is demand-driven: todo must already authorize independent,
non-conflicting child work. The facade does not queue, split, or schedule tasks.

The controller creates the bounded child execution, selects isolated source
state, starts or reuses the verified local service, validates model output, and
returns `completed`, `accepted`, `needs_codex`, or `failed`. JSON contracts and
compatibility details live in the references below.

## Workflow

1. Prefer the public `delegate` command above.
2. For compatibility-only read-only investigation, validate and run an `LCW-REQUEST/1` with
   `scripts/local_worker.py eligible|run`.
3. For the complete fake-backend flow, run `scripts/local_worker.py integrate`
   with a `CORE4-INTEGRATION-REQUEST/1`.
4. Use `CORE4-INTEGRATION-REQUEST/2` for a policy-enabled real execution; the
   runtime selects the verified cache, service, harness, and GPU island.
5. Treat `needs_codex` as a successful hand-back. Use only the compact result.

Read [read-only-contract](references/read-only-contract.md) for read-only role
or packet changes, [writable-work-contract](references/writable-work-contract.md)
for patch/acceptance changes, and [integration-contract](references/integration-contract.md)
for the complete flow.

Read `references/read-only-contract.md` before changing controller roles,
eligibility, authorization, isolation, or result semantics.

## Hard limits

- Allow only `explain`, `debug`, `review`, and `test_plan` roles.
- Writable work requires declared child scopes, isolated source state, external
  verification, and guarded parent-side acceptance.
- Never accept shell strings, recursive agents, architecture decisions,
  commits, pushes, scope expansion, or parent lifecycle actions.
- Never expose the child token in output or telemetry.
- Never download or install a backend or model. Real execution requires the
  checked production policy and an already-verified persistent model cache;
  deterministic fake execution remains available for tests.
