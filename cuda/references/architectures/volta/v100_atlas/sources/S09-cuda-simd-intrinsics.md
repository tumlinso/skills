# S09 — CUDA SIMD Intrinsics

**Version:** CUDA 12.9.1

**Locator:** packed arithmetic/comparison/saturation

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__SIMD.html

Packed byte/halfword operations expose useful semantics, but sm70 instruction expansion must be inspected. Saturating, ordinary packed and scalar arithmetic are not interchangeable.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
