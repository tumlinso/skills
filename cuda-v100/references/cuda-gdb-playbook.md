# CUDA-GDB Playbook

Use this file only after the crash route has already produced a compact crash summary and, when appropriate, a sanitizer pass.

## Wrapper

Use:

```bash
scripts/debug_cuda_gdb.sh -- ./your_bin
```

The wrapper should run `cuda-gdb` in batch mode and emit:

- `summary.txt`
- `summary.json`
- a short extracted backtrace
- the full raw log

Read the summary first. Open the raw log only if the summary says the result is ambiguous.

The batch command file should follow the crashing child by default:

- `set follow-fork-mode child`
- `set detach-on-fork off`

If the summary reports `debugger-detached-after-fork` or `debugger-no-stack-after-normal-exit`, do not treat that as evidence that the bug disappeared. It usually means the debugger never stayed attached to the crashing process.

## Escalate To CUDA-GDB When

- the binary segfaults with no useful CUDA-side evidence
- sanitizer runs clean but the binary still crashes
- you need a failing source line or short backtrace

## Batch-Mode Rules

- keep the command script fixed and concise
- capture only short backtraces and thread context
- do not default to interactive debugger sessions inside the skill
- do not dump huge logs into context when the summary already identifies the likely fault

## After The Debugger

- if the backtrace clearly identifies a host bug, fix it before CUDA tuning
- if it points at a kernel launch or kernel body, return to `compute-sanitizer` or the relevant CUDA implementation path only after the fault class is stable
