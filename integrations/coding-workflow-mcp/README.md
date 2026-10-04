# coding-workflow compatibility package

Project Control is the only model-facing product. `coding-workflow` is retained
for one compatibility release as an executable and administrative alias. The
alias forwards to Project Control's Codex profile and owner administration; it
is never registered beside `project-control` as a second live MCP server.

This directory owns only the old executable names, pre-cutover rollback
installer, and compatibility tests. It contains no database, authority
resolver, capability store, scheduler, claim logic, or migration implementation.
When Project Control is genuinely absent, old installations retain a bounded
fallback which constructs Todo Orchestrator's canonical six-tool adapter. An
installed-but-broken Project Control fails closed and never activates fallback.

The Skills-owned compatibility fallback discovers `next_task`, `inspect_task`,
`coordinate_task`, and `finish_task`. Its native routing guard omits and rejects
`delegate_task` and `collect_delegation` as temporarily inactive while preserving
internal implementations. Ordinary delegation uses configured Codex subagents;
local workers serve read-only observers. The preferred installed Project Control
CLI still forwards `serve codex`; its deployed discovery/dispatch and final public
surface are separately qualified by PC-SURFACE/API-03/API-04 and paired SQA.
Explicit gates use `coordinate_task(action="run_gates")`; required gates also
run during completion. Recovery is out of band and uses no model-held approval.

See [native skill routing](../native-skill-routing.md) for access and handoffs.

## Historical install and rollback

```bash
python integrations/coding-workflow-mcp/scripts/install.py
```

This installer is retained to restore an old installation during the PCU-V1
compatibility window. The Project Control installer owns candidate construction
and final atomic cutover. No PCU repository implementation task runs either
installer against the live runtime.

## Migrate one repository

```bash
python integrations/coding-workflow-mcp/scripts/migrate.py --repo <repo> --dry-run
python integrations/coding-workflow-mcp/scripts/migrate.py --repo <repo> --apply
```

The script forwards to Project Control's dry-run-first migration API. The
compatibility package has no second copy of migration rules. No repository is
migrated automatically.

## Owner recovery

```bash
coding-workflow-admin recover --repo <repo> [--task <id>] --reason "<reason>"
coding-workflow-admin recover --repo <repo> --reason "inspect" --inspect-only
```

The historical command forwards to `project-control admin recover`. On an old
installation where Project Control is absent, the bounded fallback calls Todo
Orchestrator's canonical owner API. Mutation still requires a TTY and exact
confirmation.
