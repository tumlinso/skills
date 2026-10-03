# S26 — NCCL LL128 implementation

**Version:** NCCLv2.18.6-1

**Locator:** payload/flag movement and waits

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/nccl/v2.18.6-1/src/collectives/device/prims_ll128.h

Warp-cooperative payload and progress handling form a complete protocol. Borrowing polling or volatile operations without its ordering, channel and target assumptions is not a correctness argument.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
