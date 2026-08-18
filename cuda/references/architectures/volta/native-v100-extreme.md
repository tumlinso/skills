# Native V100 Extreme Optimization

Use this route when the goal is to make the native V100 path better than the
old `cuda-v100` compatibility shim.

## Native Volta Doctrine

1. Fuse aggressively when the alternative writes intermediates back to HBM.
2. Keep sparse and glue-heavy paths custom early.
3. Split only when registers, occupancy, or a library boundary force it.
4. Build `sm_70` only while doing deep native tuning.
5. Keep one hot kernel per TU when deep inspection is likely.
6. Summarize ptxas and SASS signals before reading raw dumps.

## Fusion Bias

Fuse on Volta when:

- extra passes would round-trip through HBM
- launch count is a visible limiter
- the working set is irregular enough that library handoff adds overhead
- the intermediate state can stay in registers or shared memory

Split instead when:

- register pressure causes sustained spill or occupancy collapse
- one stage clearly belongs to cuBLAS, cuSPARSE, cuDNN, or NCCL
- synchronization boundaries already exist
- the fused kernel becomes too wide to inspect or benchmark sanely

## Code Shape Rules

- One hot kernel per `.cu` when profiler or dump work is expected.
- Put lane-role contracts, fragment layouts, and iterator invariants in narrow
  headers.
- Use short comments only to point at behavior-sensitive files or constraints.
- Record accepted performance incursions explicitly.

## Memory And Branch Notes

For every serious native kernel, record:

- which intermediates stay in registers
- which intermediates stay in shared memory
- which values intentionally round-trip through HBM
- whether divergence is intentional and cheaper than specialization
- where branch shape changes with row bins, tile classes, or sparse structure

## Native Debug And Dump Loop

1. Run `scripts/common/check_single_kernel_tu.py`.
2. Split with `scripts/split_cuda_translation_unit.py` if needed.
3. Emit a narrow profile build with `scripts/architectures/volta/emit_profile_build.py`.
4. Profile representative runs first.
5. Dump PTX or SASS only on the isolated kernel.
6. Summarize ptxas chatter with `scripts/architectures/volta/summarize_ptxas_verbose.py`.
7. Summarize filtered SASS with `scripts/architectures/volta/summarize_sass_hotspot.py`.
8. Filter objdump-style output with `scripts/common/filter_objdump_sections.py` only if the summaries still leave the decision unclear.

## Load Next

- `references/addendum-kernel-mechanics.md`
- `references/addendum-kernel-roofline-lab.md`
- `references/addendum-ptx-routing.md`
- `references/common/code-organization.md`
- `references/architectures/volta/fusion-and-specialization.md`
- `references/architectures/volta/register-pressure-and-occupancy.md`
- `references/architectures/volta/native-benchmark-loop.md`
