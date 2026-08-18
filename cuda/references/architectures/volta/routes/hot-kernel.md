# Volta Hot-Kernel Route

Use for one hot kernel, one `ncu` limiter, or post-structure tuning.

Do first:

1. If `ncu/summary.json` exists, prefer `scripts/common/recommend_cuda_route.py --arch volta --ncu ...`.
2. If the classifier says `memory-bound`, fix bytes moved or fusion depth before instruction tuning.
3. If it says `compute-path mismatch`, switch to `references/architectures/volta/routes/tensor.md`.
4. If it says `register-limited` or `shared-memory-limited`, keep the route here.

Load order:

1. `references/addendum-kernel-roofline-lab.md`
2. `references/v100_cuda_cpp_optimize.md` only for concrete kernel mechanics after the limiter is classified
3. `references/architectures/volta/register-pressure-and-occupancy.md` only for spill or occupancy-specific follow-on
