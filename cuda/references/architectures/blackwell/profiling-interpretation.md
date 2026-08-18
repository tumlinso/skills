# Blackwell Profiling Interpretation

Use this route when the first problem is reading Nsight output on B100 or
B200-class hardware.

## Ask First

- did the Blackwell-specific build target change the hot path
- did FP4 or low-precision routing actually fire the intended Tensor Core path
- is the limiter really one kernel or the GB200 deployment shape
