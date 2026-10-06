# A01 — Index by computational need

> Enter through the problem, not through a presumed CUDA implementation.

**Status:** source-backed synthesis. **Depth:** 0.
**Read when:** search, routing, index.
**Prerequisites:** none. **Evidence:** original synthesis; see linked mechanisms.

## Query routes

| Need | Mechanisms | Compositions | Required depth | Tests | Decision cue |
|---|---|---|---|---|---|
|Sparse support / intersections|M01 M02 M06 M26|C00 C11 C37|R15|E11 E13|Start with packed logic; test tensor expansion only when reuse repays it.|
|Branchless sequence routing|M03 M04 M06 M07|C01 C02 C03|R06|E05 E13|Choose symbol encoding and lane ownership before control flow.|
|Small graph propagation|M14 M02 M29|C05 C24|R06|E14 E39|Register patches for local work; monotone merges only for the right algebra.|
|State machines / local dynamics|M01 M14 M30|C06 C10 C25|R15|E13 E16|Discrete circuits and continuous algebra are different representations.|
|Tiny dense algebra|M24 M25 M27|C10 C13 C16|R05|E09 E12|Inspect four native products and downstream fragment ownership.|
|Reduction / scan / threshold|M02 M26 M29|C12 C37|R15|E11 E12|Compare shuffle/POPC with tensor or carry-save constructions.|
|Lookup / category decoding|M03 M04 M23|C03 C31|R04|E05 E26|Register network, constant broadcast and texture have distinct regimes.|
|Packing / bounded integer math|M08 M09 M11|C07 C08 C09|R15|E01 E13|Prove carry, range and sign behavior before benchmarking.|
|Register pressure / operand ports|M12 M13 M14 M20|C17 C35|R02|E04 E30|Optimize the operand-read graph and state lifetime together.|
|Latency hiding / complementary pipes|M16 M15 M36|C18 C19|R14|E02 E03 E17|Overlap required work; do not add peak throughput figures.|
|Shared layout / transpose|M18 M25 M22|C16 C36|R05|E06 E09|Compose producer/consumer maps rather than canonicalizing every stage.|
|GPU-resident scheduling|M30 M15 M17 M33|C25 C34|R06|E16 E32|Compare a small resident palette to batching and graph replay.|
|Cross-GPU cooperation|M34 M35 M31|C20 C21 C22 C23|R07|E18 E19 E20|Compare pull, owner-compute, staging and information reduction.|
|Queues / publication / arbitration|M29 M31 M38|C04 C22 C24|R06|E14 E15 E22|Reservation, publication, reuse and progress are separate.|
|DMA / non-SM computation|M36 M37 M38 M39|C26 C27 C28|R09|E27 E28 E29|Separate observed HAL behavior from header-only and speculative interfaces.|
|Address-space tricks / memory tiers|M40 M41 M42 M43|C29 C30|R08|E08 E23 E24|Naming, backing, policy and coherence are distinct.|
|Approximation / mixed precision|M10 M28 M09|C14 C15 C31|R15|E10 E26|Budget actual arithmetic error; refine ambiguous decisions.|
|Metadata elimination|M02 M03 M14|C04 C35 C36|R01|E05 E13|Let stable position carry identity instead of loading indexes.|
|Dynamic adaptation|M46 M47 M42 M52|C32 C33|R12|E25 E33|The feedback signal must repay observation and switching.|
|Firmware / hidden engines / reset|M49 M50 M51|C39|R13|E34 E35 E38|Establish an accessible contract before treating silicon as capacity.|
|Compiler / binary manipulation|M48 M12 M13|C17 C34|R10|E30 E36 E37|Pin sm70 binaries and validate the complete executable.|
|Uncertain hardware behavior|M22 M34 M39|C38 C39|R00|E07 E18 E38|Look up the open question; do not silently invent a premise.|

## Conditional source reads

Read S03 for an exact ISA/target contract; S04 for historical empirical microarchitecture; S12/S15 for copy-engine fields versus observed commands; S27 for QMD fields; S20 for tensor numerical caveats; S16 for ATS/MMU implementation. These are different evidence classes.

Do not read every source just because a card lists it. Resolve the claim that could change the design. Mandatory correctness dependencies remain mandatory even when performance evidence can be deferred.
