# Ampere Router

Assume A100-class Ampere (`sm_80`) when the device is not specified. Use this
route for A100/Ampere, TF32, `cp.async`, split barriers, structured sparsity,
or a measured change caused by its larger L2.

Read existing benchmark or profiler summaries first. Use their validity and
limiter evidence to choose from the authored guidance below.

The [Ampere Programming Guide](programming-guide.md) consolidates family
behavior. Open it for staging and kernel-structure decisions, Tensor Core and
2:4 routing, memory implications, or PTX triage. For a classified kernel
limiter, consult its profiler-interpretation section; for instruction or
layout-level tuning after that, use
[Ampere low-level optimization](low-level-optimization.md).

For shared problem classes, open the focused guide: [host-device pipeline](../../systems/host-device-pipeline.md),
[memory fit](../../systems/memory-budgeting.md), [multi-GPU topology](../../systems/ddp-topology.md),
[crash triage](../../debugging/crash-debugging.md), [CPU porting](../../workloads/cpu-porting.md),
[library choices](../../common/compute-libraries.md), [NVHPC](../../specialized/nvhpc.md),
[PyTorch extensions](../../specialized/torch-extensions.md), or [PTX](../../low-level/ptx.md).
