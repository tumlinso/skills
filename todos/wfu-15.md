

<!-- todo-orchestrator:v2-managed:start -->
# WFU-15: Canonical workflow service, protocol v2, capabilities, and MCP

Task revision: `167`; current project revision is in `todo-status.md`.

## Objective
Implement the canonical in-process WorkflowKernel boundary, protocol v2 envelopes, hash-stored lineage-bound first-class capabilities, exact six-tool MCP server, fixed adapters, and compatibility shim without todo subprocess operations.

## State
- Lifecycle: `in_progress`
- Execution: `claimed`
- Parallel policy: `parallel_safe`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_protocol_mcp.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/adapters`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/capabilities.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/mcp`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/protocol.py`
- `read`: `cpp-context-compiler`
- `read`: `cuda`
- `read`: `integrations/coding-workflow-mcp`
- `read`: `local-coding-worker`
- `read`: `workflow-unification/contracts/kernel-contract-v1.md`

## Dependencies
- `checkpoint`: `WFU-KERNEL-CONTRACT-V1`
<!-- todo-orchestrator:v2-managed:end -->
