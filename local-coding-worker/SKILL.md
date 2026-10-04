---
name: local-coding-worker
description: Read-only Project Control observer and skill-mode adapter on the existing local model supervisor. Coding delegation is temporarily inactive on native model routing; internal maintenance contracts remain preserved.
---

# Local Coding Worker

## Native skill access

Native coder, mutator and scout agents read installed `SKILL.md` and its
references through filesystem/command access. Follow the skill's own routes;
indexes and graphs accelerate navigation without becoming routing authority.
No observer skill adapter or mandatory overview is needed for native use.
Record materially applied guidance during the existing context/handoff flow,
with skill hash and route relevance; a read alone remains merely consulted.
See [native routing and handoff](../integrations/native-skill-routing.md).

## Read-only observer service

Project Control's durable broker may run investigator and skill jobs through
`local_worker.observer_runtime.ObserverWorkerPort` on the existing verified local
model supervisor. Both modes have job-scoped evidence and explicit messages;
warm model residency never grants shared conversation state or child authority.
The broker owns the queue, packet store, history, attempt fences and dispatch.
The worker has `command`, `log` and shared read-only information tools only.
Skill mode reads installed `SKILL.md` and follows its maps and references through
the same sandbox. See [observer-port](references/observer-port.md).

Native model routing marks coding `delegate_task` and `collect_delegation`
temporarily inactive. The internal coding implementations and maintenance
contracts below remain available for explicit operator use; they are not the
ordinary observer job path. Reactivation requires an explicit operator decision.

## Repository workflow

For substantial repository work, use `project-control`. Ordinary delegated
research, implementation, tests and review use configured Codex subagents.
Local workers are reserved for read-only observers. The coding commands below
are retained internal maintenance examples only: invoke them solely for explicit
operator maintenance or supported bounded fallback authorization. An unavailable
local worker does not authorize local coding delegation or model escalation.

Use this skill only from an active todo parent claim. The parent retains task,
gate, acceptance, commit, and push authority.

For explicitly authorized internal maintenance, the preserved CLI is:

```bash
python <skill-dir>/scripts/local_worker.py delegate \
  --claim-token <parent-claim-token> --mode <readonly|writable> --wait --json
```

Omit `--wait` to launch explicitly authorized nonblocking subordinate child work,
then collect it by execution ID:

```bash
launch=$(python <skill-dir>/scripts/local_worker.py delegate \
  --claim-token <parent-claim-token> --mode <readonly|writable> --json)
python <skill-dir>/scripts/local_worker.py delegate \
  --collect <execution-id-from-launch> --wait --json
```

Launching twice is demand-driven: todo must already authorize separate,
non-conflicting subordinate child work. The facade does not queue, split, or
schedule project tasks.

The controller creates the bounded child execution, selects isolated source
state, starts or reuses the verified local service, validates model output, and
returns `completed`, `accepted`, `needs_codex`, or `failed`. JSON contracts and
compatibility details live in the references below.

Local delegation uses live topology to reserve a safe interference domain.
An all-connected four-GPU component is supported: a conservative allocation may
reserve that entire domain. Unknown or unsupported topology still fails closed,
and foreground work may preempt only this model service. This admission
interlock does not terminate or invalidate already-running work or an admission
that was granted before the topology changed.

## Workflow

1. Ordinary observer work uses the broker-facing read-only port. The preserved
   coding CLI below is internal maintenance only.
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
- Never claim project todos or receive a first-class run lane or role.
- Never communicate directly with sibling lanes or the run inbox.
- Never publish project decisions or run-level interfaces.
- Never participate in rendezvous or integration queues.
- Never complete, advance, block, or release the parent task.
- Return only candidate results to the parent claim; the parent accepts, rejects, integrates, validates, and publishes them.
- Never download or install a backend or model. Real execution requires the
  checked production policy and an already-verified persistent model cache;
  deterministic fake execution remains available for tests.
