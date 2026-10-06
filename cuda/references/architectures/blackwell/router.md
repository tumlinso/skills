# Blackwell Router

Assume **B100 or B200-class Blackwell**, usually `sm_100`, with deployment
questions often tied to **GB200 NVL72**.

Use this route when the user names Blackwell, B100, B200, GB200, FP4, or
family-specific Blackwell build targets.

Read existing benchmark or profiler summaries first. Use their validity and
limiter evidence to choose from the authored guidance below.

Primary sources:

- https://docs.nvidia.com/cuda/blackwell-tuning-guide/index.html
- https://developer.nvidia.com/blog/nvidia-blackwell-and-nvidia-cuda-12-9-introduce-family-specific-architecture-features/

The [Blackwell Programming Guide](programming-guide.md) consolidates family
behavior. Open it for target and fallback choices, low-precision routing,
kernel structure, PTX triage, or its profiler-interpretation section. For
instruction or layout-level tuning after classification, use
[Blackwell low-level optimization](low-level-optimization.md).

For shared problem classes, open the focused guide: [host-device pipeline](../../systems/host-device-pipeline.md),
[memory fit](../../systems/memory-budgeting.md), [multi-GPU topology](../../systems/ddp-topology.md),
[crash triage](../../debugging/crash-debugging.md), [CPU porting](../../workloads/cpu-porting.md),
[library choices](../../common/compute-libraries.md), [NVHPC](../../specialized/nvhpc.md),
[PyTorch extensions](../../specialized/torch-extensions.md), or [PTX](../../low-level/ptx.md).
For GB200 NVL72 deployment, start with the
[GB200 NVL72 system guide](../../systems/gb200-nvl72.md).
