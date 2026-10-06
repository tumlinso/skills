# PA1 local worker runtime handoff

Observed 2026-10-06T16:26:53.013125+00:00. Source: `/home/tumlinson/.agents/skills` at `95818340006dd50ef233d7c67ddca2da8eb08bc4`.

This is a current, hashed supplier inventory for the SK-PA1-HANDOFF to PC-PA1-RUNTIME seam. It records allowed candidate transfer sets and downstream consumers; it does not move, retire, or repoint source. See `runtime-handoff.json` for every path, SHA-256, byte size, Git status, consumer reference line, and baseline dirty hash.

Inventory: 149 supplier files; 42 consumer files with 120 exact matching source references. Candidate transfer set counts: `runtime-source` 43, `runtime-support` 17, `authority-contracts` 7, `source-tests` 63, `catalog-compatibility` 1.

## Receiver contract

The canonical contract is [`docs/pa1/runtime-ownership.md`](runtime-ownership.md), SHA-256 `98d8fa66634e2e688c8c1dcc39748b8c1ec09acc67da34df8923589e17547b99`. It keeps `local_worker.*` as the single module identity under Project Control ownership, requires exact source-bound receiver checks, explicit configured domain-tool roots, retained dormant writable compatibility, and parity before forwarding or retirement.

## Dependency boundary

The transfer candidates are the existing `local_worker/` implementation, runtime config and schemas, CLI/worker scripts, authority reference contracts, and source tests. SKILL metadata and entrypoint material remains in the supplier until parity, then only a coordinated one-way forward is permitted. The inventory retains evaluation outputs and other historical evidence without implying their transfer or qualification.

Todo Orchestrator, CUDA, and ctxpp remain explicitly excluded independent authorities. This handoff only records existing consumers and their required transitions; it does not copy those authorities or transfer their grants.

## Current release drift

The current `local_worker/observer_runtime.py` hash is `d3a65e54aaf4a6f0c6d38621d521ee0402aba749da4bf2a543c0df75550e580f`. The paired release record pins `ac6b0eca766863617bdeed4257e690fb89ce583cdb4199328e8234f42cff09bf` for that path (release IDs `3905649ff9b03e3acec4211553a52cf2389489e9` and `269646d2da7452adfb5750bfe9b7a3068f7ee828`), and the historical source-qualification record pins `99ebb05632b7768403e103bc32bb5f04885c86662272cef14bf83fb25e57ce8b`. Neither matches the current file. The release record's earlier `passed` status is therefore historical; it does not qualify this working source. Refresh source-bound evidence before parity claims.

## Preserved working-tree state

`integrations/native-skill-catalog.json` is dirty at the source snapshot; its exact working-tree SHA-256 is `453f904d15bf1d27d95687ca75a3e5c7b40f72af8cf954d9a6f4ba78ea60e6c3`. That baseline and every other dirty boundary file are listed under `baseline_dirty_hashes`. Keep those bytes intact until root-coordinated catalog work. No supplier files were edited for this artifact.

No model inference, GPU computation, service restart, workflow mutation, or supplier source mutation was performed for this inventory.
