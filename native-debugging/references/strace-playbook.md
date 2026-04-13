# Strace Playbook

Use this file when the problem may be at the syscall or runtime-environment boundary.

## Wrapper

Use:

```bash
scripts/debug_strace.sh -- ./your_bin
```

The wrapper should emit:

- `summary.txt`
- `summary.json`
- `raw.log`
- target `stdout.txt` and `stderr.txt`

## Use `strace` When

- the process exits before your own logging appears
- a file, permission, socket, or process-spawn problem is likely
- the loader cannot find a library or configuration file
- the crash seems to follow an OS interaction rather than pure computation

## High-Signal Failures

- `ENOENT`: missing path, config, binary, or shared library
- `EACCES` or `EPERM`: permission problem
- repeated failed `openat`, `stat`, or `execve`
- a final signal line after a narrow sequence of syscalls

## Practical Rules

- read the summary first, not the whole trace
- fix the last meaningful failing syscall before chasing later fallout
- if the trace shows a normal environment handoff and the crash is still internal, return to `gdb` or sanitizer work
