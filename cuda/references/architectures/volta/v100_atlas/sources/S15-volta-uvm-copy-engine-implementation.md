# S15 — Volta UVM copy-engine implementation

**Version:** R580.95.05

**Locator:** semaphore_release; reduction_inc; timestamp; memcopy; memset

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/580.95.05/kernel-open/nvidia-uvm/uvm_volta_ce.c

Pinned driver code emits release, increment and timestamp semaphore commands with data transfer disabled. It also demonstrates constant remapping for fill and explicit flush/pipelining choices. This is real control work outside SM kernels, not a general vector ALU or automatically callable user API.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
