# Research session — 2026-10-03

## Delivered knowledge

A modular GV100/V100 SXM2 architecture/performance atlas, with hardware reference, mechanism interpretations, original compositions, conditional-read indexes, primary-source capsules and experiment protocols. This pass emphasizes representation changes and underused/non-SM machinery rather than a conventional CUDA checklist.

## Verification boundary

Source research and CPU semantic checks are distinct. No V100 was accessed; no CUDA kernel or capability probe was compiled/run here. All GPU timing, bandwidth, peer-cache, concurrency and original performance claims remain unmeasured. The E cards describe forty experiments, not forty executable benchmark implementations.

Pinned sources include CUDA 12.9.1 APIs, CUTLASSv2.11.0, NCCLv2.18.6-1, R580.95.05 UVM and Linuxv6.12 Nouveau. Moving latest/master sources are dated and identified; their exact content must be pinned before implementation. Original research supplies empirical priors, not universal silicon guarantees.

## Outstanding material

See OPEN_QUESTIONS.md and SCOPE.md. Complete electrical schematics, full NVLink protocol, firmware ABI, all address hashes/queue capacities and a complete cross-product/aggregation survey were not established. These gaps are explicit so a future agent does not accidentally make them design premises.

## Generated verification

CPU_TEST_RESULTS.json contains actual semantic-check results. VALIDATION.json contains actual package-integrity checks. Neither represents hardware measurement. Statistics are generated from the final files rather than guessed.

## Final verification

The final CPU run passed 15 groups and 31,094 assertions. GPU timings and CUDA binary validation remain unrun. A source-table screenshot audit confirmed the historical Volta POPC latency as 10 cycles, not an intermediate 14-cycle transcription. The archived PTX 8.8 reference was checked for the four-product m8n8k4 mapping.
