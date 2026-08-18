# Native System Route

Use this route for the current development machine: **4x Tesla V100 16 GB
(`sm_70`)** on the host described by the native Volta route in `cuda`.

This is the strongest path in the skill. Do not weaken it to make the general
skill cleaner.

## Native Topology

- fast NVLink pair: `GPU0 <-> GPU2`
- fast NVLink pair: `GPU1 <-> GPU3`
- acceptable leader exchange: `GPU0 <-> GPU1` and `GPU2 <-> GPU3`
- worst steady-state paths: `GPU0 <-> GPU3` and `GPU1 <-> GPU2`

## Native Doctrine

1. Treat PCIe 3.0 as the enemy.
2. Keep high-traffic work pair-local whenever possible.
3. Bias toward aggressive fusion on glue-heavy or sparse paths.
4. Keep binaries narrow while tuning: `sm_70` only for deep native work.
5. Split into one kernel per TU when you need hard profiler or dump control.

## Use Native First For

- V100-specific optimization
- topology placement on the current host
- loader and transfer starvation on the current host
- PTX, SASS, or objdump work on Volta
- benchmarking intended to predict development-time behavior on this host

## Build Rules

- For native deep tuning, prefer `sm_70` only.
- If the question is cross-generation portability, emit a separate mixed build
  matrix instead of replacing the narrow native one.
- Do not hide native signal inside one huge multi-arch binary while profiling.

## Load Next

- `references/architectures/volta/router.md` for architecture routing.
- `references/common/code-organization.md` when generated code layout matters.
- `references/common/diagnostics-workflow.md` when the first issue is
  measurement or debugging surface quality.
