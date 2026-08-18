# Volta Benchmark Route

Use for native benchmark design, profiler interop, or summary-first measurement.

Do first:

1. Keep benchmark outputs structured.
2. Read `summary.txt` or `combined_summary.txt` before raw artifacts.
3. If `nsys` or `ncu` summaries already exist, run `scripts/common/recommend_cuda_route.py --arch volta ...` and load only the returned route.

Load order:

1. `references/architectures/volta/native-benchmark-loop.md`
2. `references/benchmark-standardization.md` only if the contract or summary shape is the question
3. `references/v100_profiling_interpretation.md` only if measurement validity is still weak
