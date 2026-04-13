# Sanitizer Builds

Use this file when the binary should be rebuilt to make memory, UB, or race bugs obvious.

## Default Host Debug Build

Prefer:

```bash
g++ -g -O0 -fno-omit-frame-pointer ...
```

On Clang, use the same baseline:

```bash
clang++ -g -O0 -fno-omit-frame-pointer ...
```

## AddressSanitizer

Use for:

- heap or stack corruption
- use-after-free
- buffer overflows
- double-free

Typical flags:

```bash
-fsanitize=address -fno-omit-frame-pointer
```

Optional:

```bash
-fsanitize-address-use-after-scope
```

## UndefinedBehaviorSanitizer

Use for:

- signed overflow assumptions
- invalid shifts
- null dereference style UB
- bad vptr or alignment issues

Typical flags:

```bash
-fsanitize=undefined -fno-omit-frame-pointer
```

## ThreadSanitizer

Use for:

- data races
- lock-order mistakes
- unsafely shared state

Typical flags:

```bash
-fsanitize=thread -fno-omit-frame-pointer
```

## Practical Rules

- Start with one sanitizer family at a time.
- `ASan` and `TSan` are usually separate builds.
- Keep symbols on and optimizations low until the fault is understood.
- Wrap the instrumented binary with `scripts/debug_crash.sh` so the sanitizer output still lands in `summary.txt` and `summary.json`.
- If symbolized stacks are missing, read `references/symbolization-playbook.md`.
