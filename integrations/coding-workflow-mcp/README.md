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

The implementation uses the official Python MCP SDK over local stdio. Server
startup imports no GPU library, initializes no model, reserves no GPU, and
scans no repository.

