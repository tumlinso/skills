# SK-WF2-L-V

Role `specialist`; workspace mode `isolated_merge`. Parent `SK-WF2-L-COORD`.

## Serial queue

1. `SK-WF2-V01` — Review donor mapping and parity evidence independently
2. `SK-WF2-V02` — Test ctxpp with no workflow products installed
3. `SK-WF2-V03` — Test forwarding shims and real consumer boundaries
4. `SK-WF2-V04` — Verify final migration after the release switch

Use the authoritative next_task/inspect_task interface for this exact local run/lane. Discover its installed signature; do not guess flags or reuse old run IDs. Read only the current task sheet, referenced contracts and changed producers. Verify required source commits are present. Return a bounded handoff with source/evidence IDs, unresolved limitations and the next safe action. Do not republish the whole transcript.

The integrator is a durable exclusive destination, never an isolated producer. Before producers finish, resolve integration-task binding and exact recorded base using the installed owner API. Serial phases may require explicit reviewed rebind or a new phase lane; do not force stale bases. The coordinator remains claimable while work is ongoing and closes after local I90; the epic is last.
