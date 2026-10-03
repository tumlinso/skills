# R00 — Reading and evidence contract

> A design search space with explicit proof and reachability gates, not an assertion that every idea is fast.

**Status:** source-backed synthesis. **Depth:** 0.
**Read when:** evidence, reading, correctness.
**Prerequisites:** none. **Evidence:** original synthesis; see linked mechanisms.


## Two independent axes

Knowledge: **A** ISA/API guarantee; **D** NVIDIA implementation; **E** original empirical result; **R** reverse engineering; **H** reasoned hypothesis; **S** speculative lead; **U** unresolved. Reachability: **C** public CUDA/Driver API; **P** inline PTX; **B** cubin/SASS work; **K** driver/channel; **F** firmware/platform. A documented K feature is not a public C feature. An H composition may use only guaranteed primitives and still lose badly.

Local verification is a third field. This research did not execute on the user's V100 s. CPU tests in the package validate algebra and index mappings, not GPU instruction lowering, tensor rounding, memory coherence or speed. Historical numbers remain attributed to their experiment. Missing values are unknown, not zero.

## Select depth by the decision

Read the need index, then two or three M cards. Read a C recipe to see a concrete representation and falsifier. Read R06 whenever work shares mutable state across lanes/blocks/devices; R15 whenever precision is repurposed; R05 whenever exact MMA fragments matter. Source headers are worth loading only when a K-level capability or disputed implementation detail changes a design choice. Never inject the entire compendium into every kernel task.

Each mechanism is interrogated for physical action, scope/granularity, cost/concurrency, CUDA/PTX/SASS exposure, avoidable conventions, alternative role, compositions, attractive representations, correctness/fragility, provenance and an experimental discriminator. These fields are distributed across linked cards rather than repeated as twelve boilerplate headings.

## Promotion ladder

Algebraic equivalence → legal operand form → participation/visibility/progress proof → generated binary inspection → isolated measurement → interference measurement → complete-workload benefit. Passing one stage does not pass the next. A speedup claim needs its shape, distribution, preprocessing reuse, accuracy and topology.

A negative result should identify the failed representation and regime. “Tensor cores are bad for graphs” is not a useful record; “this packing at this density loses after conversion” is. Preserve superseded claims and failed tests so another agent can revisit the actual premise.

## Remaining frontier

The atlas does not contain a complete SXM2 schematic, all NVLink packet/credit details, exact remote-cache policies, every queue limit or a firmware programming contract. Those questions remain indexed, not silently answered by analogy. The original 0–140 scope is retained. No meta-device implementation is chosen.
