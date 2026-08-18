# Volta Native Route

Use for generic native-V100 optimization when the bottleneck is not yet locked.

Do first:

1. If `summary.json` artifacts already exist, run `scripts/common/recommend_cuda_route.py --arch volta ...` and load only the returned route.
2. If the loss is repeated HBM passes or launch trains, load `references/architectures/volta/routes/fusion.md`.
3. If one steady-state kernel is already dominant, load `references/architectures/volta/routes/hot-kernel.md`.
4. If dense or blocked math should be on Tensor Cores, load `references/architectures/volta/routes/tensor.md`.
5. If the issue is pipeline, topology, memory fit, or crash class, stop here and switch to the matching small addendum.

Load `references/architectures/volta/native-v100-extreme.md` only when the path
is still mixed after the route is classified.
