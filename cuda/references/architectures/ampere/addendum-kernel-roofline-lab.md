# Ampere Hot-Kernel Lab

Use this route when one A100 kernel is already isolated and hot.

## Do First

1. Confirm the benchmark window is representative.
2. Check whether the limiter is Tensor Core eligibility, staging, memory passes,
   or register pressure.
3. Change only the lever that matches the limiter.
