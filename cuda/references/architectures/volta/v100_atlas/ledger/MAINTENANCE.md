# Updating the atlas

## Stable IDs and append-only evidence

Keep IDs stable. Add a claim or hypothesis instead of silently replacing an incompatible premise. For a correction, record old/new IDs, reason, source version and affected compositions. A source document, a source claim, a local result and an original hypothesis are different objects.

Required event fields: event_id, date, type, objects, summary, evidence, verification. Useful types: SOURCE_ADDED, CLAIM_ADDED, CLAIM_SUPERSEDED, HYPOTHESIS_ADDED, EXPERIMENT_RUN, NEGATIVE_RESULT, OPEN_QUESTION_RESOLVED. Do not promote H to E because a CPU identity test passed.

## Adding a measurement

Use experiments/result.schema.json and retain raw samples. Record exact hardware/software/topology, binary hashes, operating conditions, correctness and limitations. Compare a strong baseline including encoding, maintenance, synchronization and decoding. Register confidence separately for the measured regime and any extrapolation.

## Updating retrieval

Update manifest summaries/tags/prerequisites and need-index routes. Keep one card small enough to read independently. Link common correctness/numerical material instead of repeating it. A source header should be an optional deep read unless a low-level dependency changes the implementation choice.

Run tools/validate_atlas.py and tools/semantic_checks.py after edits. The manifest stores word counts and SHA256 hashes; use tools/refresh_manifest.py after intentional content changes, then validate again. The full compendium is a derived artifact; never treat it as the sole editable authority.

## Recording failure

A negative result names the representation, shape, distribution, numerical contract and failed cost/semantic assumption. Keep its raw evidence and a route from the relevant mechanism. Do not generalize “this tile lost” into “this entire hardware mechanism is useless.”

This ledger is maintained by explicit future edits. Nothing here schedules autonomous monitoring, background research or hardware experiments.
