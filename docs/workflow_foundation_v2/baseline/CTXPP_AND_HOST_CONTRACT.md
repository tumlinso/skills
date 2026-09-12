# WF2 ctxpp and host-runtime boundary

At the captured baseline, ctxpp is standalone: `ctxpp_packet.py` first tries
the optional `todo_orchestrator.runtime.capture_source_identity` helper, then
falls back to Git status plus SHA-256 hashes of the explicitly relevant files.
Neither route opens a workflow database.  A source identity is metadata
(`repo_root`, `git_head`, and dirty paths) plus a content-derived fingerprint;
the fallback's selected-file hashes are content evidence, not a claim that Git
metadata itself is content-addressed.

Read/query operations are distinct from refresh and rewrite. The ctxpp skill
defines retrieval (`status`, `where`, `route`, `slice`) as a read path; lazy
targeted refresh is a separate index operation, and canonical rewriting needs
an explicit apply intent and an existing plan. A query cache is disposable
retrieval state, never workflow authority.

`HostCoordinator` is host-local coordination for the sidecars that opt into
its runtime directory. Its CPU/RAM accounting is an advisory aggregate
admission limit within that coordinator; it neither reserves all host CPU/RAM
nor represents an OS- or cluster-wide reservation. Physical accelerator
resource IDs may be exclusive inside its host-local table. Consumers must
report this distinction rather than calling ordinary CPU/RAM requests
host-wide reservations.

Relevant baseline paths are `cpp-context-compiler/scripts/ctxpp_packet.py`,
`cpp-context-compiler/SKILL.md`,
`todo-orchestrator/todo_orchestrator/runtime/source.py`, and
`todo-orchestrator/todo_orchestrator/background/host.py`.
