# Shared-host CUDA execution

Read this before executing CUDA correctness, benchmarks, profiling, or debug
captures on the shared machine. These controls are operational invariants;
architecture and workload choices remain the agent's judgment.

MCP startup never imports GPU libraries, starts a model, reserves a GPU, scans
a repository, or runs a benchmark. Reading guidance does not authorize execution.

## Foreground work

```bash
python <skill-dir>/scripts/cuda_controller.py inspect --project <repo> --json
python <skill-dir>/scripts/cuda_controller.py run --spec <spec.json|-> --json
```

An explicit `run` preempts conflicting background activity and reserves its
GPUs atomically. Campaign state is project-local; physical GPU, profiler,
interference-domain, and host-pressure interlocks are host-global. Runtime
device identity/topology governs selection. `CUDA_VISIBLE_DEVICES`, a short
standalone reservation, or `with_benchmark_mutex.sh` alone does not establish
exclusive controller admission or quiescence.

Keep builds in `benchmark.build_argv`; they run before the GPU lease. Top-level
`build_argv` is rejected. An explicit unusable toolkit fails rather than
silently selecting another; compiler and sanitizer come from the same toolkit.
Read [controller spec contract](controller-background-contract.md#foreground-build-and-toolkit-contract-2026-09-06)
for `binary_paths`, `command_cwd`, and Todo gate integration. A bound gate must
run through its supported controller integration; direct runs do not waive it.

For a direct Compute Sanitizer check, the foreground schema uses `argv` for the
target, `benchmark.build_argv` for an optional build, `recipe` for the wrapper,
`resources` for host admission, and `toolchain` for compiler/sanitizer
validation. This accepted spec shape requires replacing the repository,
toolkit, and target placeholders with real project and validated toolkit paths:

```json
{
  "schema_version": 1,
  "project_root": "/path/to/repository",
  "command_cwd": "/path/to/repository",
  "recipe": "compute-sanitizer",
  "toolchain": {
    "root": "<validated-toolkit-root>",
    "require_sanitizer": true
  },
  "benchmark": {
    "build_argv": ["cmake", "--build", "build", "--target", "my_cuda_test"]
  },
  "argv": ["./build/my_cuda_test", "--input", "data/example.bin"],
  "correctness_argv": ["./build/my_cuda_test", "--self-test"],
  "resources": {"gpus": 1, "cpu_threads": 4}
}
```

Replace the placeholders with real project paths, a usable toolkit root, and a
test case compatible with the target GPU and host driver. For V100 `sm_70`, see
the CUDA 12.x [Volta build rules](../architectures/volta/optimization-guide.md).
The toolkit root must contain a usable `bin/nvcc` and matching
`compute-sanitizer`; `require_sanitizer` makes missing or unusable sanitizer
support fail before admission. `argv` and `correctness_argv` are argument
arrays, not shell command strings. Run the example through `python <skill-dir>/scripts/cuda_controller.py
run --spec <spec.json> --json`, replacing `<skill-dir>` with this skill's
absolute path. Set the sanitizer executable from that same validated toolkit
in the controller process environment when invoking it:

```bash
COMPUTE_SANITIZER_BIN="<validated-toolkit-root>/bin/compute-sanitizer" \
  python <skill-dir>/scripts/cuda_controller.py run --spec <spec.json> --json
```

The wrapper checks `COMPUTE_SANITIZER_BIN` first, then its pinned host path,
then `PATH`; setting `PATH` alone may select a different sanitizer. The
controller inherits this environment, validates the toolkit, runs the optional
build, then admits the sanitizer wrapper under GPU and profiler interlocks.

Before timing/profiling, the controller requires consecutive idle samples from
the runtime-selected GPU UUIDs. Foreign compute processes, utilization, or a
quiescence timeout invalidate clean measurement. Timed benchmarks and
system-wide profiling use the host-wide exclusive gate. Controller-selected
Nsight Compute runs pass their admitted UUIDs and use a shared host gate plus
exclusive locks for those UUIDs, acquired in sorted order. Captures on distinct
devices may overlap when their requested PCIe and NVLink isolation domains do
not conflict. The default profiler isolation remains enabled; set
`resources.isolate_pcie_root` and `resources.isolate_nvlink_domain` to `false`
only for independent resident work. Same-device captures remain excluded by
controller reservations and wrapper locks.

Calls to `profile_ncu.sh` without controller-provided device scope and UUIDs
retain host-wide exclusion. New wrappers recognize both owner-specific intent
records and the legacy singleton marker. A device capture already in progress
may finish its finite run when a host measurement queues; new device captures
yield to that host intent. Background timing yields to any foreground
measurement intent, and background device profiling yields to host intents and
overlapping UUID intents. Other profiler and debugger recipes keep their
existing host scope. Wrappers add coordination inside an admitted run; they do
not replace controller admission, resource reservations, or quiescence.

## Background campaigns

```bash
python <skill-dir>/scripts/cuda_controller.py background arm --spec <spec.json|-> --json
python <skill-dir>/scripts/cuda_controller.py background enqueue --spec <spec.json|-> --json
```

Arming is explicit and persistent. Once armed, relevant task completion,
checkpoint, and handoff events wake private correctness/benchmark work without
polling or changing Todo output. Read [background specs](controller-background-contract.md)
only when authoring these campaigns. Use `background backfill --spec ...` once
for project-supplied historical task/source/benchmark mappings; it does not
rewrite Todo history.

Correctness repeats and fails fast; failure skips its dependent measurement
chain while unrelated watches can proceed. Healthy background results remain
silent. Failures, material regressions, missed targets, serious variance or
contamination, and relevant bottlenecks produce bounded evidence. The agent
interprets conflicts and decides promotion.

## Evidence and source context

```bash
python <skill-dir>/scripts/cuda_controller.py evidence <id> --project <repo> --focus <topic> --json
```

Summaries point to authoritative raw artifacts. Read
[performance facts](performance-facts.md) when selecting/comparing baselines:
compatibility keys, source/binary provenance, contamination, and candidate
promotion have different roles.

Generated context views are read-only; edit canonical source. The controller
uses cpp-context-compiler for small semantic source slices and falls back to
`scripts/split_cuda_translation_unit.py` when semantic retrieval is unavailable.
For accepted changes, prefer a performance-intent ctxpp task packet carrying
changed paths plus task/campaign identity before the slice/TU fallback.

For CUDA knowledge, follow the authored links in [SKILL.md](../../SKILL.md),
then search filenames/headings with ordinary filesystem tools. The controller's
compatibility `guide` command is not the semantic routing authority.
