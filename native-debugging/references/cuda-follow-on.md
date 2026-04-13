# CUDA Follow-On

Leave this skill when the fault is clearly CUDA-specific.

## Route Into `cuda-v100` When

- the user asks for `compute-sanitizer`, `cuda-gdb`, Nsight Systems, or Nsight Compute
- stderr mentions illegal memory access, launch failure, device assert, or driver/runtime CUDA errors
- the host backtrace only identifies CUDA launch or synchronization boundaries

## Read Next

- `cuda-v100/SKILL.md`
- `cuda-v100/references/addendum-crash-debugging.md`
- `cuda-v100/references/compute-sanitizer-playbook.md`
- `cuda-v100/references/cuda-gdb-playbook.md`
- `cuda-v100/references/crash-signature-map.md`

## Route Boundary

- Keep host-native debugging here.
- Keep device-side debugging in `cuda-v100`.
- Do not duplicate CUDA scripts inside `native-debugging`.
