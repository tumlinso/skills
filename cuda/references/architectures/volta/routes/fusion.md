# Volta Fusion Route

Use for fuse or split or specialize or graphs questions on native V100.

Rules:

1. Bias toward fusion when the alternative rereads or rewrites full tensors through HBM.
2. Use CUDA Graphs only after obvious fusion and grouping opportunities are exhausted.
3. Accept moderate divergence when the split would add launch trains and memory passes.
4. Split only when spills, occupancy collapse, or stable workload classes clearly win.

Load order:

1. `references/architectures/volta/fusion-and-specialization.md`
2. `references/addendum-kernel-mechanics.md` only if launch-vs-divergence or memory-tier tradeoffs stay unclear
3. `references/roofline-launch-bound-patterns.md` only if the remaining question is graphs vs grouped launches
4. `references/addendum-kernel-roofline-lab.md` only after structure is basically right
