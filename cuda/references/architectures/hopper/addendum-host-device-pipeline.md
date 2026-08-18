# Hopper Host-Device Pipeline

Use this route when H100 is being starved.

## Order

1. Prove starvation with Nsight Systems.
2. Fix loader and staging trouble before touching clustered kernels.
3. Revisit TMA only after the device-side path is representative.
