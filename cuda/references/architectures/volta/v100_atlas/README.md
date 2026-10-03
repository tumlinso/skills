# V100 / SXM2 Software Circuit-Bending Atlas

Begin with **START_HERE.md**, then **NEED_INDEX.md**. **FIELD_GUIDE.md** explains the representation-first approach. The full Markdown compendium is an archival option, not the default model context.

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

CPU semantic checks: 15 groups, 31,094 assertions passed in the final authoring run. Hardware experiments remain unrun. The capability probe is source-only, uncompiled and unexecuted here. No novel GPU speedup, synchronization behavior, shader binary or proprietary tensor rounding behavior is claimed to have been locally validated.

All primary-source URLs, versions and locators are in sources/. Original ideas are separated from the established mechanisms that motivate them. Third-party papers, source trees and font files are not bundled. A source link is a locator, not a guarantee that a moving upstream page remains unchanged.
