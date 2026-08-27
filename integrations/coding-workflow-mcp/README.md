# coding-workflow compatibility package

`coding-workflow` is the only ordinary model-facing workflow protocol.
Todo-orchestrator is its in-process transactional kernel. This directory owns
only installation, the legacy Python entry-point shim, repository migration,
owner-command wiring, and compatibility tests. It contains no second backend,
capability database, claim logic, scheduler, or recovery semantics.

The discovered MCP surface is exactly `next_task`, `inspect_task`,
`coordinate_task`, `delegate_task`, `collect_delegation`, and `finish_task`.
Explicit gates use `coordinate_task(action="run_gates")`; required gates also
run during completion. Recovery is out of band and uses no model-held approval.

## Install and rollback

```bash
python integrations/coding-workflow-mcp/scripts/install.py
```

The installer builds an isolated venv, preserves the prior registration in an
owner-only rollback file, registers the canonical entry point, verifies
`codex mcp list --json`, and initializes through the official MCP client. A
failed smoke restores the prior registration.

## Migrate one repository

```bash
python integrations/coding-workflow-mcp/scripts/migrate.py --repo <repo> --dry-run
python integrations/coding-workflow-mcp/scripts/migrate.py --repo <repo> --apply
```

Migration replaces only the marked AGENTS section and adds
`configuration.workflow_front_door = "coding-workflow"` to an existing project
identity. It is idempotent and preserves user guidance, plans, IDs, gates, and
architectural constraints. `--remove` reverses only those additive changes.
No repository is migrated automatically.

## Owner recovery

```bash
coding-workflow-admin recover --repo <repo> [--task <id>] --reason "<reason>"
coding-workflow-admin recover --repo <repo> --reason "inspect" --inspect-only
```

Mutation requires a TTY and exact confirmation. The canonical recovery engine
refuses live work, preserves dirty artifacts, and records sanitized audit state.
