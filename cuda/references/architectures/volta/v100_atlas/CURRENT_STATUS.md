# Current evidence status

> Dated 2026-10-06 from the portable evidence packet at source commit `5b5629b001da4a42d6f41a84d94f73c07a29d478`. The original navigation, protocols, and full compendium remain preserved separately.

The portable campaign evidence contains 40 experiment records with these overall statuses: CPU_ONLY=6, GPU_RUN=29, NOT_RUN=5. GPU-run records are E02, E03, E05, E06, E07, E08, E09, E10, E11, E12, E13, E14, E15, E16, E17, E18, E19, E20, E21, E22, E23, E24, E25, E26, E31, E32, E33, E37, E39. A GPU_RUN status covers only the implemented and measured subset recorded for that experiment; it does not complete the original protocol. CPU_ONLY and NOT_RUN results retain their distinct scope. COMPILED_ONLY remains an individual subcase where the source card records one (including E36's compiled-image inspection); it is not promoted to a whole-experiment status. The records do not establish biological validation or blanket composition speedups.

Read the [dated context for R00](reference/R00-current-status-context.md), [claim limits](experiments/CLAIM_LIMITS.md), and [result interpretation](experiments/INTERPRETING_RESULTS.md) before using measurements to support a broader claim. Campaign and source identities are recorded in [provenance](experiments/evidence/v100-20261006/provenance.json).
