# C27 — Command-engine completion arithmetic

> Use a non-SM actor for narrow progress-state operations.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** semaphore, DMA, control, non-SM.
**Prerequisites:** M38 M31 R09 R06. **Evidence:** S12 S15 S17.

## Construction [H; reachability K; public C alternatives]


The pinned Volta HAL already emits semaphore release, increment and timestamp commands with payload transfer disabled. The copy-class header additionally names unsigned/signed reduction operations such as MIN, MAX, XOR, AND, OR and ADD. Treat the observed HAL forms and the broader declared menu as different evidence strengths.

A candidate pipeline can publish a phase count or update a control word without launching a tiny shader. Establish exact INC/DEC threshold/wrap semantics, flush behavior, target scope and command ordering before using them. These operations act on the semaphore target, not every element of a buffer.


## Why it could work

The copy engine is demonstrably capable of control work independent of bulk copy. A bounded control sequence might spare SM residency or avoid a kernel boundary while preserving data-engine progress.

## Full cost and strongest baseline

Compare public stream memory operations, events and a tiny kernel. Deeper command submission can cost more than the saved work. Different engine timestamps are not automatically comparable with GPU global timer or another device.

## Falsifier / rejection condition

Reject any “general DMA ALU” interpretation. Reject if only a private unsafe route is available, if ordering cannot be proved, or if the whole pipeline fails to beat supported alternatives.

**Experiment:** E28 E22. This composition has not been benchmarked on a V100 here.
