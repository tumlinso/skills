# R13 — Electrical, firmware and reliability frontier

> Keep the less-public platform questions visible without inventing a schematic.

**Status:** source-backed synthesis. **Depth:** 3.
**Read when:** SXM2, electrical, firmware, RAS, reset.
**Prerequisites:** none. **Evidence:** S02 S28 S36 S37 S38 S39 S40.


The whitepaper documents module-level identity, nominal power, memory and interconnect organization. Management APIs expose some runtime identity, telemetry and reset controls. Original driver sources reveal pieces of graphics/context initialization, authenticated bootstrap, MMU, FIFO and fault handling. This is meaningful evidence below CUDA, but not a transistor-level machine description.

Missing are a validated complete SXM2 pin map, VRM schematic, strap matrix, PLL graph, al lO EM differences and full NVLink framing/credits. Exact module/baseboard part numbers and firmware matter. Connector form factor does not prove identical routing or enabled features.

Software-visible consequences include negotiated links/PCIe widths, sustained clocks, power competition and group recovery. A reset may affect connected peers. ECC events, retired pages, link retries and thermal throttling can contaminate a benchmark. Do not infer a speed benefit from disabling ECC; HBM sideband ECC differs from older arrangements.

Embedded controllers have real jobs and privilege boundaries. Their existence is not evidence that arbitrary user code can use them as spare cores. An exposed control/telemetry interface can still be a useful slow supervisory plane. Study boot/reset to locate the boundary between silicon, firmware and driver policy before proposing modifications.

Graphics/raster/media appropriation remains SKU/interface-gated. Texture interpolation through a documented CUDA path is a much firmer candidate than assuming an inaccessible codec or shader stage exists on this Tesla product.

The frontier ledger includes exact remote-cache behavior, HBM/L2 hashing, queue depths, raw instruction forms, firmware ABI and engine-reset granularity. A targeted source or experiment may resolve one. Repetition of a plausible story does not.
