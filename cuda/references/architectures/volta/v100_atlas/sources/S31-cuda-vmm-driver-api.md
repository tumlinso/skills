# S31 — CUDA VMM Driver API

**Version:** CUDA 12.9.1

**Locator:** allocation granularity; map; setaccess; unmap

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-driver-api/group__CUDA__VA.html

Capabilities/granularity and allocation handles/mappings/permissions are distinct. Remapping must obey lifetime and synchronization contracts. Alias accessibility is not a promise of coherent concurrent use through every view.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
