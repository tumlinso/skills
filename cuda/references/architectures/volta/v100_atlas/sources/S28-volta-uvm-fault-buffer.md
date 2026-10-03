# S28 — Volta UVM fault buffer

**Version:** R580.95.05

**Locator:** overflow and GET handling

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/580.95.05/kernel-open/nvidia-uvm/uvm_volta_fault_buffer.c

A concrete implementation comment requires advancing GET before clearing overflow because a same-cycle arriving fault can reassert it. Control queues have timing/ordering contracts; overflow is not an application scheduling primitive.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
