# S22 — CUTLASS sm70 MMA implementation

**Version:** CUTLASSv2.11.0

**Locator:** 8×8×4 inline PTX forms

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/cutlass/v2.11.0/include/cutlass/arch/mma_sm70.h

Explicit Volta MMA specializations expose row/column and accumulator forms. A logical group size of 8 does not remove the warp-wide instruction participation requirement.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
