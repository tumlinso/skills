# CUDA Controller Background Contract

Read this only when arming, explicitly enqueueing, or backfilling a CUDA
background campaign. Commands accept JSON from a file or `-` and return compact
JSON. Project queues and evidence remain private under
`.todo-orchestrator/runtime/`; physical reservations are host-global.

## Arm once

```json
{
  "schema_version": 1,
  "project_root": "/project",
  "watch": {
    "task_ids": [],
    "task_prefixes": ["CUDA-"],
    "paths": ["src/**/*.cu", "include/**/*.cuh"],
    "symbols": []
  },
  "benchmark": {
    "build_argv": ["cmake", "--build", "build", "--target", "cudaBench"],
    "argv": ["./bench", "--json"],
    "correctness_argv": ["ctest", "--test-dir", "build", "-R", "cuda"],
    "correctness_repetitions": 3,
    "correctness_minimum_seconds": 15,
    "correctness_maximum_repetitions": 64,
    "metric": "latency_ms",
    "direction": "minimize",
    "practical_regression_percent": 2.0,
    "target": null,
    "warmups": 1,
    "repetitions": 5,
    "gpus": 1
  },
  "policy": {
    "initial_characterization": true,
    "benchmark_completed_steps": true,
    "max_background_gpus": 4,
    "max_deep_profiles_per_revision": 2
  }
}
```

The agent supplies the real correctness command, benchmark, objective, watched
scope, threshold, and any candidates. The controller does not infer among
plausible production benchmarks.

`build_argv` is optional and always runs as CPU-heavy work without reserving a
GPU. For compatibility, a `correctness_argv` using `ctest --build-and-test ...
--test-command ...` is split automatically at `--test-command`: the build is a
bounded CPU stage and only the test command reserves a GPU. Ready correctness
work takes priority over additional builds, so the first available binary can
begin using a GPU while other targets compile. Correctness runs at least three
times and for up to 15 seconds by default, bounded at 64 repetitions. It stops
at its first failure and skips that revision's dependent benchmark/profile
stages while independent watches continue. Set the correctness bounds
explicitly when another validation intensity is justified.

Ready measurements outrank additional builds. Benchmark and profiler jobs share
one host-global scheduling resource, so jobs waiting for serialized timing do
not reserve otherwise usable GPUs.

## Explicit revision enqueue

Use `background enqueue --spec ...` for one revision. `source_revision` is a
Git commit-ish and is archived without changing the worktree. Without it, a
clean current worktree is required unless `allow_dirty` is explicitly true.

```json
{
  "schema_version": 1,
  "project_root": "/project",
  "watch_id": "watch-id",
  "mapping": {
    "task_id": "CUDA-17",
    "source_revision": "abc123",
    "todo_revision": 42,
    "initial_characterization": false
  }
}
```

## One-time backfill

Use `background backfill --spec ...` with project-supplied mappings. Repeating
the same request is deduplicated. A mapping may override the watch benchmark
contract for that revision. Backfill writes only private campaign state and
does not alter historical todo tasks or events.

```json
{
  "schema_version": 1,
  "project_root": "/project",
  "watch_id": "watch-id",
  "mappings": [
    {
      "task_id": "CUDA-OLD",
      "source_revision": "v1.2.0",
      "todo_revision": 10,
      "benchmark": {"argv": ["./bench", "--dataset", "old.json"]},
      "initial_characterization": true
    }
  ]
}
```

Pause, resume, and stop operate on project watches. Enqueueing while paused is
durable but does not wake work; stopped watches reject new revisions.

## Foreground build and toolkit contract (2026-09-06)

Foreground `run` accepts one structured `benchmark.build_argv`. It executes
before GPU reservation; a nonzero build exits without acquiring an accelerator.
Top-level `build_argv` is rejected. `binary_paths` records SHA-256 values of the
specified project files after the build. `toolchain` accepts `root` and
`require_sanitizer`; an explicit unusable toolkit fails rather than silently
selecting another version. Compiler and sanitizer resolve from the same toolkit.
`command_cwd` may select an existing subdirectory within the project.

Todo command gates may declare a `cuda` object with controller resources,
`toolchain`, `build_argv`, and `binary_paths`. Both explicit gate execution and
completion reruns then use the canonical controller. Such gates must expect exit
zero and leave Todo's separate `resources` list empty. The controller holds the
host reservation and benchmark mutex during execution and writes a lease receipt
for the child. A temporary project wrapper is no longer required.
