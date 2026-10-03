# R09 — The non-SM command machine

> Copy engines and launch descriptors expose restricted transformations and control, not merely transport.

**Status:** source-backed synthesis. **Depth:** 3.
**Read when:** DMA, QMD, driver, firmware, non-SM.
**Prerequisites:** none. **Evidence:** S12 S13 S15 S27 S37 S39 S40.


The copy class inS12 includes component remapping, constants, write suppression, pitch/block-linear addressing and conditional controls. This can be interpreted as a limited format transformer. A plausible experiment copies records directly into a consumer-friendly layout while SMs compute. It is not evidence of arbitrary gather/scatter or a public cudaMemcpy remap API.

S15 is stronger evidence for a second role: actual Volta UVM code emits semaphore release, increment and timestamp commands with payload transfer disabled. Thus a non-SM actor can perform completion-state work. Crucially, the reduction applies to the semaphore word, not every element of an array. A “DMA vector ALU” inference would be wrong.

The QMD definition inS27 contains circular-queue, dependent-descriptor, release-slot/reduction and resource/cache fields. Those expose a richer front end than a single opaque launch. They do not supply complete rules for reference counts, queue ownership, units, cancellation or self-modification. A scheduling-mask field is not automatically a mapping to CUDA `%smid`.

A disciplined escalation is public copies/events/graphs/stream memory operations; shader-based movement; exact cubin experiments; validated driver/channel construction; platform/firmware work. Performance can justify a deeper route, but layer depth is not itself an optimization. Compare public graph replay before building a QMD path.

Texture/surface facilities are immediately relevant where CUDA exposes them. Raster, media and embedded controllers need separateS KU/API/firmware evidence. Physical ancestry or an engine class in a source tree is not usable Tesla capacity. The productive question is: what operation already exists in this unit, and can useful semantics be encoded in its operands?
