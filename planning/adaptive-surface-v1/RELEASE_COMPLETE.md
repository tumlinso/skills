# Standalone paired AS1 release completion

The controller executed qualification, live installation and release gates for
both authorities. The functional candidate is
`as1-paired-3905649-269646d-20261005`, pinning standalone Project Control
`3905649ff9b03e3acec4211553a52cf2389489e9` and Skills
`269646d2da7452adfb5750bfe9b7a3068f7ee828`. Its immutable candidate manifest SHA256
is `0a968d2456e5a576ef0fc74c05b0543f4479c27385caa800e083018f507bbc34`.
Skills contains no Project Control gitlink or second source checkout.

The bound Skills paired manifest passed against actual Q14 inference proof,
the original native Skills qualification stdout and the controller's actual
live release proof. Native Skills PIN-01/PIN-02 passed (14 tests, 0.31 seconds),
and native Project Control REL-01/REL-02/REL-03 passed. The sanitized
[release summary](validation/skills-paired-release.json) records exact receipt,
manifest and native stdout hashes. The native PIN stdout reference identifies
the actual executed result; no replacement gate run was performed.

Actual installation exposed the consolidated `project-control` registration.
The controller exercised `new -> old -> new` launcher rollback and retained an
accepted native job using an isolated native fixture with dispatch paused and
the forward store preserved. This establishes the bounded fixture rollback
claim, not preservation of arbitrary production workloads. No Todo database
was restored. Protected service/process identities and GPU devices 0 and 2
were preserved, alongside unrelated work and the paused NF1A state.

Q14 integrated inference qualified retained packet continuation, restart,
eviction and exact/poll lookup behavior. Two queued jobs completed and one
returned an explicit partial result (`finding_requires_observed_packet`).
Historic Q11 skill evidence is reused only for model-owned entry/maps
traversal and exact source/hash/range/excerpt provenance with documented source
equivalence. Its narrative synthesis remains non-authoritative and unverified:
entailment was false, the frontend result was partial (`synthesis_budget`),
and a narrative fusion claim cited the wrong line. The original failed
qualification archives remain intact. No biological validation, broad
performance improvement or arbitrary synthesis quality claim follows from
these gates.

The controller closed `SK-AS1-0000` with validated disposition at Skills
revision 1008; `SK-AS1-RUN-1` completed with all 14 required child closure gates.
Project Control closed `PC-AS1-0000` at revision 904; its run completed with
all 10 required child closure gates.

Large Skills `finish_task` replies can exceed the existing 8192-byte workflow
response budget and return `workflow_response_too_large` after successful
native completion. This occurred for release and epic closure on the new
runtime. Persisted receipts, task outcomes and run state remain authoritative;
the controller verified them without rerunning successful gates. This
preserved workflow response-budget behavior is separate from the corrected
observer job checkpoint/restart behavior.

The accepted installation instructions in
`PAIRED_RELEASE.md` remain unchanged so their bound hash stays valid.
Raw inference archives, private stores, databases and credentials are excluded
from this source publication.
