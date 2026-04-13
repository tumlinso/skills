# Symbolization Playbook

Use this file when the logs already contain raw addresses, offsets, or mangled symbols.

## Core Tools

- `addr2line`
- `c++filt`
- `nm`
- `readelf`
- `objdump`

## Common Commands

Map an address to file and line:

```bash
addr2line -Cfpie ./your_bin 0xADDRESS
```

Demangle a C++ symbol:

```bash
printf '%s\n' '_ZN...' | c++filt
```

List exported and local symbols:

```bash
nm -an ./your_bin
```

Inspect shared-library dependencies and build IDs:

```bash
readelf -Wn ./your_bin
readelf -Wd ./your_bin
```

Disassemble around a symbol:

```bash
objdump -Cd ./your_bin
```

## Decision Rules

Use symbolization before guessing when:

- the backtrace contains `??`
- the binary is stripped but build IDs and debug files exist
- the failing frame is in a shared object and you need the exact offset

## Practical Notes

- make sure the binary and debug info are from the same build
- keep frame pointers on for first-pass debugging
- if sanitizer stacks are unsymbolized, install or point to `llvm-symbolizer`
