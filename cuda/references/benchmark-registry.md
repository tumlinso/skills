# CUDA benchmark registry

Use a project-owned `CUDA-BENCHMARK-REGISTRY/1` file when the same build,
correctness, and measurement contract should be reused across todo work,
accepted local-worker patches, and direct source changes. The registry is
configuration, not a second task system. Todo-orchestrator remains authoritative
for work and the CUDA controller remains authoritative for campaign execution.

Each campaign declares logical targets, repository-relative path globs, exact
ctxpp symbol identities, optional todo task selectors, structured commands, one
JSON metric path, and a resource request. GPU UUIDs are optional; prefer a count
and architecture so runtime topology discovery can select the physical devices.
Never encode assumed GPU pairs.

```json
{
  "format": "CUDA-BENCHMARK-REGISTRY/1",
  "schema_version": 1,
  "project_root": "/project",
  "campaigns": [
    {
      "id": "fused-attention-sm70",
      "description": "Correctness and latency for the Volta implementation",
      "targets": ["fused-attention"],
      "paths": ["src/attention/**/*.cu", "include/attention/**/*.cuh"],
      "symbols": ["c:@N@demo@F@fused_attention#"],
      "task_ids": [],
      "task_prefixes": ["CUDA-"],
      "build": {"argv": ["cmake", "--build", "build", "--target", "attentionBench"]},
      "correctness": {"argv": ["ctest", "--test-dir", "build", "-R", "attention"], "repetitions": 3},
      "benchmark": {"argv": ["./build/attentionBench", "--json"], "warmups": 1, "repetitions": 5},
      "metric": {
        "format": "CUDA-METRIC/1",
        "schema_version": 1,
        "name": "latency_ms",
        "path": "latency_ms",
        "direction": "minimize",
        "unit": "ms",
        "practical_regression_percent": 2.0,
        "target": null
      },
      "resources": {"gpu_count": 1, "architecture": "volta"},
      "policy": {"initial_characterization": false}
    }
  ]
}
```

Validate without creating watches or jobs:

```bash
python cuda/scripts/cuda_controller.py registry validate \
  --registry cuda-benchmarks.json --json
```

Discovery accepts a small evidence object. `changed_paths` are direct Git
changes, `todo_scopes` are todo ownership scopes, and only patch results with
`accepted: true` contribute `changed_paths`. A readonly
`CTXPP-CONTEXT-PACKET/1` contributes its canonical target `id`, `name`, and
`signature`. Logical `targets` and todo `task_ids` use exact identifiers.

```json
{
  "schema_version": 1,
  "changed_paths": ["src/attention/fused.cu"],
  "todo_scopes": ["include/attention"],
  "accepted_patches": [
    {"accepted": true, "changed_paths": ["src/attention/dispatch.cu"]}
  ],
  "context_packets": [],
  "targets": ["fused-attention"],
  "task_ids": ["CUDA-17"]
}
```

```bash
python cuda/scripts/cuda_controller.py registry discover \
  --registry cuda-benchmarks.json --input discovery.json --json
```

Without `--input`, discovery reads tracked and untracked changes relative to
`--base HEAD`. It is read-only unless `--auto-queue` is supplied. Auto-queue is
permitted only when exactly one campaign matches. Zero matches return
`no_match`; multiple matches return `ambiguous` with the matching evidence and
create no watch, queue, claim, or resource lease. The controller never ranks or
guesses among plausible production benchmarks.
