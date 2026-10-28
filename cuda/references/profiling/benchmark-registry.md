# Historical CUDA benchmark registry

This page preserves the former campaign format and its evidence-selection
methodology. The controller that validated, discovered, and executed these
registries has been retired. No current scheduler adapter consumes this format,
so the examples below help interpret existing registries and receipts; they do
not define an active runner. For new bounded execution, follow [host execution](../execution/host-execution.md) and submit a Device Scheduler job directly. Todo-orchestrator
remains authoritative for task ownership and acceptance.

In the historical format, campaigns declared logical targets, repository-relative
path globs, exact ctxpp symbol identities, optional task selectors, structured
commands, metrics, and resource requests. UUIDs could be omitted in favor of
architecture/count discovery. These fields are not a current Device Scheduler
request; never submit a legacy registry directly as a job spec.

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
      "binary_paths": ["build/attentionBench"],
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
      "parameters": {
        "size": {"type": "integer", "minimum": 1, "maximum": 1048576, "default": 4096},
        "tier": {"type": "enum", "values": {"small": "small", "large": "large"}, "default": "small"}
      },
      "policy": {"initial_characterization": false}
    }
  ]
}
```

The retired observer-probe interface substituted bounded parameter values
into registered command arguments. Dataset values named registry-owned sources
rather than caller-supplied paths. These details are retained to explain
historical campaign records; no active probe or registry-validation command is
provided.

The former discovery interface accepted a small evidence object. changed_paths
were direct Git changes, todo_scopes were Todo ownership scopes, and only patch
results marked accepted contributed paths. Read-only context packets supplied
canonical target identity. Logical targets and task IDs used exact identifiers.
The shape below is retained as historical evidence, not an active scheduler
request.

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



Historically, discovery read tracked and untracked changes relative to HEAD.
Its optional auto-queue path required exactly one match; zero matches returned
no_match, and multiple matches returned ambiguous without creating work. Those
behaviors describe the retired controller and are not available through
Device Scheduler.
