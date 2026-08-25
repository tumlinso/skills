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
