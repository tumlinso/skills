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

The discovered MCP surface is exactly `next_task`, `inspect_task`,
`coordinate_task`, `delegate_task`, `collect_delegation`, and `finish_task`.
Explicit gates use `coordinate_task(action="run_gates")`; required gates also
run during completion. Recovery is out of band and uses no model-held approval.

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
