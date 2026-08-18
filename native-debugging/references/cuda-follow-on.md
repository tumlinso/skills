# CUDA Follow-On

Leave this skill when the fault is clearly CUDA-specific.

## Route Into `cuda` When

- the user asks for `compute-sanitizer`, `cuda-gdb`, Nsight Systems, or Nsight Compute
- stderr mentions illegal memory access, launch failure, device assert, or driver/runtime CUDA errors
- the host backtrace only identifies CUDA launch or synchronization boundaries

## Read Next

- `cuda/SKILL.md`
- `cuda/references/addendum-crash-debugging.md`
- `cuda/references/compute-sanitizer-playbook.md`
- `cuda/references/cuda-gdb-playbook.md`
- `cuda/references/crash-signature-map.md`

## Route Boundary

- Keep host-native debugging here.
- Keep device-side debugging in `cuda`.
- Do not duplicate CUDA scripts inside `native-debugging`.
