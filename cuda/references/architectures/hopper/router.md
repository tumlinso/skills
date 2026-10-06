# Hopper Router

Assume **H100-class Hopper**, usually `sm_90`.

Use this route when the user names H100 or Hopper, or when the optimization
hinges on TMA, thread block clusters, distributed shared memory, FP8, or DPX.

Read existing benchmark or profiler summaries first. Use their validity and
limiter evidence to choose from the authored guidance below.

Primary source:
https://docs.nvidia.com/cuda/hopper-tuning-guide/index.html

The [Hopper Programming Guide](programming-guide.md) consolidates family
behavior. Open it for TMA and cluster ownership, staging, FP8 or DPX routing,
memory and topology implications, or PTX triage. For a classified kernel
limiter, consult its profiler-interpretation section; for instruction or
layout-level tuning after that, use
[Hopper low-level optimization](low-level-optimization.md).

For shared problem classes, open the focused guide: [host-device pipeline](../../systems/host-device-pipeline.md),
[memory fit](../../systems/memory-budgeting.md), [multi-GPU topology](../../systems/ddp-topology.md),
[crash triage](../../debugging/crash-debugging.md), [CPU porting](../../workloads/cpu-porting.md),
[library choices](../../common/compute-libraries.md), [NVHPC](../../specialized/nvhpc.md),
[PyTorch extensions](../../specialized/torch-extensions.md), or [PTX](../../low-level/ptx.md).
