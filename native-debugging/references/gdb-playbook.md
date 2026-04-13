# GDB Playbook

Use this file after a compact crash summary says the next move is a short backtrace.

## Wrapper

Use:

```bash
scripts/debug_gdb.sh -- ./your_bin
```

The wrapper should emit:

- `summary.txt`
- `summary.json`
- `raw.log`
- `commands.gdb`

Read `summary.txt` first.

## Escalate To GDB When

- the process dies with a host signal
- the sanitizer rerun still leaves the fault ambiguous
- you need the top frame, source line, locals, or thread context

## Batch Rules

- keep the command script concise and repeatable
- capture a short backtrace, not an interactive session
- prefer child-following for forked reproducers
- do not paste full debugger transcripts into context when the summary already isolates the fault

## After The Backtrace

- fix the top user frame first when it is clear
- symbolize unresolved frames before guessing
- if the top frames are CUDA launch boundaries or device-fault shims, route into `references/cuda-follow-on.md`
