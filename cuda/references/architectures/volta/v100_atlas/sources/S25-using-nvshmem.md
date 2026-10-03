# S25 — Using NVSHMEM

**Version:** retrieved2026-10-03; version-sensitive

**Locator:** symmetric addresses; CUDA model; transport prerequisites

**Evidence type:** primary

**Source:** https://docs.nvidia.com/nvshmem/api/latest/using.html

A symmetric pointer is local to its PE; remote addressing includes translation. GPU-side puts/gets/signals have explicit ordering and transport contracts. GPU-originated NIC communication has requirements beyond simply owning NVLink.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
