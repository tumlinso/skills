# Ubuntu Install Components

Use this file when the environment is missing core debugging tools.

## Baseline Packages

Install these first on Ubuntu 24.04-style systems:

- `build-essential`
- `gdb`
- `binutils`
- `strace`
- `linux-tools-common`
- `linux-tools-generic`
- `cmake`
- `ninja-build`

For `perf`, also make sure the running-kernel tools package is present when Ubuntu splits it per kernel release:

- `linux-tools-$(uname -r)`

## Sanitizer-Friendly Toolchains

Install at least one compiler toolchain with sanitizer support:

- `gcc`
- `g++`
- `clang`
- `llvm`

`ASan`, `UBSan`, and `TSan` come from the compiler runtime; they are not separate Ubuntu packages in the same way `gdb` or `strace` are.

## Useful Optional Packages

- `lldb`
- `valgrind`
- `rr`
- `elfutils`

Install debug-symbol packages for libc, libstdc++, and any large third-party libraries you debug frequently. Package names are distro- and version-specific, so treat those as target-environment choices rather than hardcoded requirements here.

## CUDA Follow-On Components

Only install these if the issue truly belongs in `cuda-v100`:

- NVIDIA driver matching the GPU and kernel
- CUDA Toolkit or NVIDIA HPC SDK that provides `cuda-gdb`
- `compute-sanitizer`
- Nsight Systems
- Nsight Compute

## Current Host Snapshot

On the current host, these commands are already present:

- `gdb`
- `strace`
- `perf`
- `addr2line`
- `readelf`
- `objdump`
- `nm`
- `g++`
- `cmake`
- `cuda-gdb`
- `compute-sanitizer`
- `nsys`
- `ncu`

These are not currently exposed on the path:

- `clang++`
- `llvm-symbolizer`
- `valgrind`
- `rr`
- `lldb`

## Environment Notes

- `perf` may require a less restrictive `kernel.perf_event_paranoid` setting.
- Sanitizers produce better stacks when frame pointers are preserved.
- If sanitizer stacks are unsymbolized, install `llvm-symbolizer` and point the sanitizer runtime at it.
