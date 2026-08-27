# Workflow Unification v3 Rollback Record

## Frozen stable state

- Authoritative skills checkout: `/home/tumlinson/.agents/skills`
- Stable source and remote `main`: `d956052dff0c15867e8ab99be4a6b41fcb72f091`
- Pinned bootstrap todo CLI: `/home/tumlinson/.agents/skills/todo-orchestrator/scripts/todo.py`
- Pre-plan todo project UUID: `460468fe-ee72-4a64-a565-87cfec640d0c`
- Pre-plan todo revision: `132`
- Pre-plan snapshot is preserved by commit `d956052d` and has SHA-256 `8ef76a866255e3efbb98905e8d1eff2d571108886d710ec5361771a6d2b9b4ef`.
- Installed MCP registration: `coding-workflow` runs `/home/tumlinson/.local/share/coding-workflow-mcp/venv/bin/python -m coding_workflow_mcp` with `CODING_WORKFLOW_SKILLS_ROOT=/home/tumlinson/.agents/skills`.
- Stable integration source: `/home/tumlinson/.agents/skills/integrations/coding-workflow-mcp`.
- Project-control stable source: `/home/tumlinson/project-control` at `9d1d4dd2e265f29cb292943b78bc6475d34be6f4`.

The original checkout and installed runtime are not implementation targets before `WFU-31`. The stable todo CLI above remains the bootstrap coordinator until the new kernel passes integration and dogfood gates.

## Development rollback

Before cutover, rollback means stopping work through the current claim lifecycle while preserving the `workflow-unification-v3` branch, worktree, todo events, patches, and evidence. Never reset, clean, delete, or rewrite either worktree or the shared todo database. The unrelated C4Q history remains untouched.

## Cutover rollback

`WFU-31` must capture the immediately pre-cutover MCP registration and installed package artifact again. If installed smoke validation fails, restore that captured package/entry point and the registration above, verify `codex mcp list`, and leave the validated branch and evidence intact. Do not migrate user repositories during rollback.

Rollback is not authorized before a failed cutover gate, and no old compatibility shim may be removed until installed validation succeeds.
