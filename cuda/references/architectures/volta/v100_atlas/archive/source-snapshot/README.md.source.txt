# V100 / SXM2 Software Circuit-Bending Atlas

Begin with **START_HERE.md**, then **NEED_INDEX.md**. **FIELD_GUIDE.md** explains the representation-first approach. The full Markdown compendium is an archival option, not the default model context.

The [experiment review index](experiments/README.md) now links all forty cards to the completed 2026-10-06 V100 campaign and explains their measured coverage. Each card separates observations, implications for representation and execution, and limits. The [central claim-limits index](experiments/CLAIM_LIMITS.md) lists what this run cannot establish alongside the narrower statements its evidence supports; a [JSON index](experiments/claim_limits.json) contains the same entries. Read the [interpretation guide](experiments/INTERPRETING_RESULTS.md) before treating a measured subset as validation of an entire proposed protocol. Portable summaries are checked in; raw samples and profiler captures remain local.

Edition 1.0, researched and assembled 2026-10-03. The package contains 16 reference chapters, 52 mechanism cards, 40 original composition hypotheses, 40 experimental protocols, 42 source capsules, and machine-readable ledgers. The original 0–140 research domains plus appended domains are retained in the scope ledger; the earlier 71-domain plan is also preserved.

Python tools require Python 3.10+ and the standard library only:

```sh
python tools/read_atlas.py search "branchless sequence routing"
python tools/read_atlas.py read M01 C01 --budget 1800 --refs
python tools/semantic_checks.py
python tools/refresh_manifest.py
python tools/validate_atlas.py
```

Run refresh before validation after editing a document. The SHA256SUMS file describes this release; local edits intentionally change those hashes.

Original authoring record (2026-10-03): CPU semantic checks passed 15 groups and 31,094 assertions; hardware experiments were then unrun and the capability probe was source-only. The [original release](https://github.com/tumlinso/gpu_circuit_bending_atlas/tree/5c1f805db80a81f7476ede8292abba69821d104f) preserves that record. Later campaign evidence is separately dated and bound to benchmark source commit `f223c51dcfacab602e9bc68b3e65cc75730dc7f8`; it supports the implemented cases and stated contracts, not every original hypothesis or sweep.

All primary-source URLs, versions and locators are in sources/. Original ideas are separated from the established mechanisms that motivate them. Third-party papers, source trees and font files are not bundled. A source link is a locator, not a guarantee that a moving upstream page remains unchanged.
