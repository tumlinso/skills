# S17 — CUDA stream memory operations

**Version:** CUDA 12.9.1

**Locator:** WaitValue/WriteValue/BatchMemOp warnings

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-driver-api/group__CUDA__MEMOP.html

Stream memory waits/writes have capability and address restrictions; managed pointers are excluded. Dependencies created only by these operations are invisible to CUDA scheduling, so CUDA-visible ordering may also be required to prevent deadlock. Remote flush is conditional.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
