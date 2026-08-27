# Workflow Semantic Read v1

`todo semantic workflow --json` is the additive, read-only normalized workflow view consumed by project-control. SQLite remains authoritative; consumers must not join workflow tables independently to infer activity.

The response reports `active_run_id`, run/lane trees, serial queues, roles, authoritative dispatch observations, blocking messages and questions, rendezvous arrivals, managed workspaces, integration queue/conflicts, recovery-needed records, context cursors, safe parallel groups, and subordinate local-worker children.

A first-class agent appears in `first_class_agents` only when an active session, active dispatch, active matching claim and lane task, fresh heartbeat, positive context version, and required workspace are all present. A ready or claimed task alone is insufficient.

Local-worker executions appear only in `local_children`, keyed to their parent claim/task and parent lane when available. They are never lanes, roles, run participants, messages, or rendezvous arrivals.

Unavailable pre-v10 state returns `available: false` with an explicit reason. The command is read-only, includes a serialized SQLite authority fingerprint, and exposes no capability hashes, tokens, approval material, packets, logs, transcripts, GPU identifiers, or model endpoints.
