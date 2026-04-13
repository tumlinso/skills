---
name: native-debugging
description: "Standalone Linux-first C and C++ debugging skill for crash triage, sanitizer builds, batch `gdb` backtraces, symbolization, syscall tracing, and lightweight CPU-side `perf` diagnosis. Use when Codex needs to debug native binaries, tests, libraries, or mixed host-side failures in C/C++ code on Linux. Route CUDA-specific crashes, `compute-sanitizer`, or `cuda-gdb` requests to `cuda-v100` after the native host-side failure surface is classified."
---

# Native Debugging

Use this skill for Linux-native debugging of C and C++ code.

Keep `SKILL.md` small. Treat it as a router. Load only the reference that matches the current failure surface.

## Workflow

1. Classify the dominant problem first.
   - crash, abort, or assertion
   - sanitizer build and rerun
   - short backtrace or failing source line
   - raw addresses or mangled symbols
   - syscall or file/process boundary problem
   - CPU-side runtime diagnosis
   - CUDA-specific crash that should leave this skill

2. Read `references/debug-workflow.md`.
   - use it to choose the shortest path to a compact first answer

3. Run `scripts/debug_crash.sh` first when the target crashes or exits abnormally.
   - capture `summary.txt` and `summary.json` before opening raw logs

4. If the target should be rebuilt with sanitizers, read:
   - `references/sanitizer-builds.md`
   - then `references/asan-ubsan-tsan-playbook.md`

5. If a short backtrace is needed, read `references/gdb-playbook.md`.
   - use `scripts/debug_gdb.sh`

6. If the problem is about symbols or raw addresses, read `references/symbolization-playbook.md`.

7. If the failure may be about files, syscalls, process creation, or dynamic loading, read `references/strace-playbook.md`.
   - use `scripts/debug_strace.sh`

8. If the binary runs but the user needs a quick CPU-side performance diagnosis, read `references/perf-playbook.md`.
   - use `scripts/debug_perf.sh`

9. If the failure is actually CUDA-specific, read `references/cuda-follow-on.md` and route into `cuda-v100`.

10. If the environment is missing tools, read `references/install-components-ubuntu.md` and run `scripts/check_debug_toolchain.sh`.

## Script Map

Prefer these scripts over ad hoc command strings:

- `scripts/debug_crash.sh`
  - capture stdout, stderr, signal, exit code, environment, and a compact crash summary
- `scripts/debug_gdb.sh`
  - run `gdb` in batch mode and emit a short backtrace-oriented summary
- `scripts/debug_strace.sh`
  - collect a compact syscall trace and summarize likely missing-path or permission failures
- `scripts/debug_perf.sh`
  - run lightweight `perf stat` collection and emit a short CPU-side counter summary
- `scripts/classify_native_failure.py`
  - classify crash, `gdb`, `strace`, and `perf` outputs into compact text and JSON summaries
- `scripts/combine_debug_summaries.py`
  - combine multiple debug summaries into one short decision
- `scripts/check_debug_toolchain.sh`
  - report installed versus missing native debugging tools on Ubuntu-like systems

## Output Requirements

Be explicit about:

- the failing command or reproducer
- whether the result is conclusive
- the likely failure class
- the next tool or next fix
- which summary file should be read first
- whether the issue stays in this skill or should route into `cuda-v100`
