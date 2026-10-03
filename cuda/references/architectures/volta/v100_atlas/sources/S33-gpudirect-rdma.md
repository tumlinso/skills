# S33 — GPUDirect RDMA

**Version:** CUDA 12.9.1

**Locator:** BAR; registration; IOMMU; memory ordering

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/gpudirect-rdma/index.html

External DMA requires registration, lifetime and ordering discipline. BAR size and root topology matter. A kernel polling external writes is not automatically a correctly ordered shared-memory protocol.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
