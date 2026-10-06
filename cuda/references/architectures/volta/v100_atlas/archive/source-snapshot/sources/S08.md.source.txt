# S08 — CUDA Integer Intrinsics

**Version:** CUDA 12.9.1

**Locator:** __fns;__dp4a;__dp2a;__byte_perm; shifts; popcount

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__INT.html

Integer APIs include packed dots, set-bit search, permutation, multiply-high and funnel shifts. __fns has a base/offset contract and 0xffffffff no-result sentinel. CUDA byte_perm does not expose every PTX prmt selector behavior. Intrinsic names do not guarantee one SASS instruction.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
