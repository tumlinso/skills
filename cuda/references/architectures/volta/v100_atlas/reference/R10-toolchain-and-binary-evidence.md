# R10 — Toolchain and binary evidence

> Preserve a known sm70-producing toolchain and audit the executed path.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** compiler, SASS, CUDA, libraries.
**Prerequisites:** none. **Evidence:** S05 S06 S11 S14 S22 S23 S26 S34 S41.


S06 distinguishes hardware lifetime from compiler targets: CUDA 12.9 retains offline sm70 compilation; CUDA 13 drops targets below 7.5. R580 is the stated final older-architecture driver branch. This does not promise every current cuB LAS, P y Torch, Triton, NCCL or inference binary retains Volta kernels. Compiler, driver, library build and selected path must all agree.

For experiments prefer an explicit native sm70 cubin and record whether a PTX JIT fallback was used. Management tooling's displayed CUDA version need not be the installed compiler. Preserve ptxas version, flags, driver, library version, kernel resource usage and binary hash.

Disassemble the hot loop, not just a representative instruction. Check register count, spills, shared allocation, code size, predicates, conversions and actual memory operations. Clear high-level code may already produce the desired sequence; inline PTX can prevent useful compiler work. Conversely, one clever expression can expand into a slow selection network.

For B-level transformations preserve original and edited binaries plus a deterministic transform. Resource metadata, relocations, constants, global state, branch/call targets and dependency controls are part of correctness. Random output tests are necessary but insufficient for memory-order or variable-latency scheduling assumptions.

The atlas uses pinned CUTLASSv2.11.0, NCCLv2.18.6-1 an dR580.95.05 source as evidence, not a deployment mandate. Moving open-gpu-doc headers are date-stamped but not commit-pinned; capture exact commit/hash before constructing commands. Current profiler/MPS documentation can describe features unavailable on the installed Volta stack. Compatibility is an explicit experiment, not a broad family-name assumption.
