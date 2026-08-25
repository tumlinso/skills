# coding-workflow

`coding-workflow` is a local stdio MCP compatibility facade over the existing
todo-orchestrator, cpp-context-compiler, local-coding-worker, and CUDA public
interfaces. It owns no repository, task, source-index, worker, or GPU state.

The v1 MCP surface is exactly five tools:

- `next_task`: bootstrap or resume todo and atomically claim safe work.
- `inspect_task`: refresh bounded task, source, or evidence context.
- `delegate_task`: opportunistically request nonblocking local assistance.
- `collect_delegation`: nonblockingly collect one returned delegation handle.
- `finish_task`: apply exactly one authoritative todo disposition.

Only opaque workflow and delegation capabilities cross the MCP boundary. Raw
todo secrets, worker tokens, GPU identifiers, endpoints, packets, logs, and
transcripts remain behind the facade. Existing skill CLIs remain supported as
fallback and debugging interfaces.

Workflow capabilities are durable across stdio server restarts and package
reinstalls. If Codex loses a workflow handle while the facade-owned todo claim
is still active, call `next_task` with the same repository and explicit task ID.
The facade validates the stored claim through todo, reissues a fresh opaque
handle, and returns the current compact task capsule without a second claim.
Terminal `finish_task` removes all aliases for that claim. The facade never
returns or reconstructs the underlying todo secrets in model context.

## Emergency live-lease recovery

**The live-lease override cannot be accessed without explicit manual permission
for that exact live claim. It is an emergency recovery mechanism, not normal
`next_task` behavior.** A boolean, ordinary MCP argument, repository path, or
task ID is never authorization.

When `next_task` reports `override_requires_permission`, a human owner may use
an interactive terminal to create one short-lived, one-use approval:

```bash
python integrations/coding-workflow-mcp/scripts/recovery_admin.py approve \
  --repo <repo> --task-id <task-id> --reason "lost opaque workflow handle"
```

The CLI displays the exact non-secret claim fingerprint and revision and
requires the human to type the task ID. The returned `toa_...` capability may
then be supplied once as `next_task.recovery_approval`. Approval is bound to the
canonical repository, todo project, task, claim incarnation, project revision,
requesting UID, reason, and expiration. It is created and consumed inside
todo-orchestrator's transaction authority; coding-workflow cannot create or
self-approve it.

Recovery is refused if ownership is not verifiably `coding-workflow`, the claim
or project changed, or any child execution, guarded acceptance, gate execution,
resource/auxiliary lease, or background/CUDA campaign remains attached. A
successful override preserves task semantics and evidence, records a sanitized
audit, replaces only the claim incarnation, and returns a fresh opaque workflow
handle. Raw todo and approval tokens are never returned in the task capsule.

`delegate_task.target` is a bounded delegation objective. It is not forwarded
as a literal ctxpp target: local-worker independently derives an authorized
source path from the capsule or selected scopes when one is proven and
otherwise omits the ctxpp target and returns `not_eligible` before admission.
The narrow objective is composed with, rather than substituted for, the parent
todo objective. Child delegations receive only a relevant subset of 1–16
parent-authorized scopes.

The implementation uses the official Python MCP SDK over local stdio. Server
startup imports no GPU library, initializes no model, reserves no GPU, and
scans no repository.

## Install

```bash
python integrations/coding-workflow-mcp/scripts/install.py
```

The idempotent installer creates an isolated venv under
`~/.local/share/coding-workflow-mcp/venv`, registers the local stdio server as
`coding-workflow`, verifies `codex mcp list`, and initializes the server through
the official MCP client SDK.

## Add repository routing

```bash
python integrations/coding-workflow-mcp/scripts/migrate.py --repo <repo> --dry-run
python integrations/coding-workflow-mcp/scripts/migrate.py --repo <repo> --apply
```

Use `--remove` to remove only the marked coding-workflow section. Migration
preserves task plans, IDs, gates, architectural constraints, and all existing
direct-CLI fallback instructions.
