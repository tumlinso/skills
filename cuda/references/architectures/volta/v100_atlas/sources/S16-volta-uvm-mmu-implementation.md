# S16 — Volta UVM MMU implementation

**Version:** R580.95.05

**Locator:** PTE apertures; NO_ATS; page levels

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/580.95.05/kernel-open/nvidia-uvm/uvm_volta_mmu.c

Code distinguishes video/coherent-system/peer apertures and 47-bit physical addressing. In ATS systems, NO_ATS directory policy spans 512 MB virtual regions to prevent CPU translation from defeating intended GPU faults. This is platform-specific, not an ordinary CUDA PTE-editing interface.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
