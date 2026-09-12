# SK-WF2-L-I

Role `integrator`; workspace mode `exclusive`. Parent `SK-WF2-L-COORD`.

## Serial queue

1. `SK-WF2-I10` — Publish the donor baseline and test inventory
2. `SK-WF2-I20` — Integrate and publish the standalone ctxpp contract
3. `SK-WF2-I40` — Integrate forwarding shims and engine consumers
4. `SK-WF2-I60` — Publish consumer-ready paired release acceptance
5. `SK-WF2-I90` — Close Skills work after qualified deployment

Use the authoritative next_task/inspect_task interface for this exact local run/lane. Discover its installed signature; do not guess flags or reuse old run IDs. Read only the current task sheet, referenced contracts and changed producers. Verify required source commits are present. Return a bounded handoff with source/evidence IDs, unresolved limitations and the next safe action. Do not republish the whole transcript.

The integrator is a durable exclusive destination, never an isolated producer. Before producers finish, resolve integration-task binding and exact recorded base using the installed owner API. Serial phases may require explicit reviewed rebind or a new phase lane; do not force stale bases. The coordinator remains claimable while work is ongoing and closes after local I90; the epic is last.
