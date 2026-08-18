# Ampere Host-Device Pipeline

Use this route when A100 is being starved.

## Order

1. Prove starvation with Nsight Systems.
2. Classify the stall as loader, collation, pinned-memory, copy fragmentation,
   or NUMA trouble.
3. Fix batching and overlap before touching kernels.
4. Revisit `cp.async` only after the device-side path is representative.
