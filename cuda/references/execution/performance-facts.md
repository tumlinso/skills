# CUDA performance facts and clean measurement

`CUDA-PERFORMANCE-FACT/1` is a reusable measurement fact, not work authority
and not a substitute for raw benchmark output. Facts live in the CUDA
controller's private runtime store and carry hashes and paths for every raw
stdout/stderr record. Todo-orchestrator continues to own tasks and accepted
gate evidence.

## Compatibility

Facts compare only when their exact compatibility keys match. The key covers:

- registered campaign and benchmark identity;
- metric path and minimize/maximize direction;
- warmup and repetition protocol;
- project-declared workload and toolchain identity when using a direct
  controller spec;
- runtime-discovered GPU model, compute capability, memory, driver, device
  count, and selected topology class.

Source fingerprints, commits, binary hashes, GPU UUIDs, PCI addresses, and
physical indices remain provenance. They are intentionally excluded from the
compatibility key: source and executable identity must differ for previous and
candidate revisions to be comparable, while UUID/index changes alone must not
hard-code a host layout. A registry campaign ID must identify one stable
dataset/precision/shape contract. Direct controller specs may additionally put
those axes in `benchmark.compatibility` and name the build environment with
`benchmark.toolchain_id`.

Baseline selection is deterministic. An explicitly requested accepted fact is
used only if compatible. Otherwise the newest compatible fact is selected in
this order: `accepted`, `previous`, then `historical`. `candidate` facts are
recorded but never silently promoted to baselines. A backfill mapping may set
`accepted_baseline: true`; other backfilled measurements are `historical`.
Incompatible or missing facts produce an absent baseline rather than a guessed
comparison.

The fact ID is visible in stored CUDA evidence. A direct background watch may
pin it with `benchmark.accepted_baseline_fact_id`. Backfill is the supported
way to label an older source measurement: use `accepted_baseline: true` on the
one accepted mapping; unmarked mappings remain historical. The legacy
`baseline:<watch>` metadata is still written for compatibility, but new
classification never treats that unkeyed first result as comparable evidence.

## Measurement safety

Before timing or profiling, the controller requires consecutive idle samples
from the runtime-selected GPU UUIDs. Any foreign compute process, utilization,
or timeout makes the measurement contaminated and prevents fact creation.
Topology is discovered at runtime; no physical GPU pair is assumed. Foreground
intent still preempts conflicting background reservations before quiescence is
sampled.

Correctness remains first and fail-fast. Its repetition count adapts from the
observed per-run duration to meet both the declared minimum count and minimum
duration, capped by the declared maximum. A material regression or missed
target requests an Nsight Systems timeline. Nsight Compute is queued only when
that timeline identifies a concrete hot kernel. Severe variance requests a
clean repeat before profiling.
