# Shared-host CUDA execution through Device Scheduler

Device Scheduler is the single authority for host resource admission and
supervised execution. Read this before launching CUDA correctness, profiling,
benchmark, sanitizer, or debug work. Project Control still authorizes project
work and owns task state; Device Scheduler owns execution and physical resource
allocation.

The former `cuda_controller.py` entrypoint is retired after cutover. It is a
fail-closed tombstone, not a compatibility proxy. Historical controller
receipts remain archival evidence and do not describe current ownership.

## Submit a bounded job

Create a normal Device Scheduler `JobSpec` JSON object and submit it through
the installed CLI:

```bash
device-scheduler job submit --payload-file job-spec.json
```

Use argument arrays and an explicit working directory. Request the stable GPU
UUID discovered by Device Scheduler, with a positive `gpu_memory_bytes`
admission estimate. Use `mode: "exclusive"` and the `gpu.exclusive` tag for
whole-device work. A GPU memory request is admission accounting; the NVIDIA
adapter does not claim hard VRAM enforcement. Request CPU cores and host memory
when the workload needs supervised cgroup limits. Declare finite timeouts and
restart/cancellation behavior explicitly.

For profiling and clean timing, include the adapter precondition supported by
the configured NVIDIA adapter:

```json
{
  "name": "gpu.quiescence",
  "schema_version": 1,
  "parameters": {
    "timeout_seconds": 60,
    "interval_seconds": 1,
    "consecutive_samples": 3,
    "max_utilization_percent": 0
  }
}
```

A precondition is checked against the actual granted GPU descriptors immediately
before launch. Unsupported or stale telemetry blocks the job; do not replace
that refusal with device visibility variables, a mutex, or an unmanaged launch.

To retrieve current execution state and retained output, use the same authority:

```bash
device-scheduler job get <job-id>
device-scheduler job wait <job-id> --timeout-seconds 30
device-scheduler job logs <job-id>
```

Wait timeout does not cancel a job. Use `device-scheduler job control <job-id>
cancel` for an authorized cancellation and wait for verified cleanup before
assuming its resources are available. Unknown execution or reclamation state
remains unavailable pending reconciliation.

## Profilers and measurements

Existing wrappers such as `profile_ncu.sh` remain as in-job coordination tools.
They preserve profiler scope, capture interlocks, and evidence formatting, but
they do not allocate GPUs, preempt work, or prove quiescence. Invoke them only
inside a supervised job that already has the required grant and precondition.
Keep Nsight Compute, Compute Sanitizer, compiler, and CUDA toolkit paths explicit
in the job's argument/environment contract. A missing tool or unsupported
adapter guarantee is a failed admission, not permission to fall back.

Keep correctness checks separate from timing. Preserve source, binary, command,
profiler, sanitizer, result, and Device Scheduler receipt identities in the
project's evidence records. Scheduler receipts establish the admitted attempt,
actual grant, logs/results, and cleanup evidence; they do not prove a performance
claim beyond the captured measurement.

## Background work

Submit recurring or event-triggered work as Device Scheduler schedules only
when an operator has explicitly authorized the campaign and its bounded policy.
Do not use retired controller `background arm`, `enqueue`, or `backfill`
commands. Project Control tasks remain the acceptance authority; scheduler job
completion is execution evidence, not task acceptance.


## Historical controller records

The following references explain preserved legacy campaign evidence only;
their controller operations are retired:

- [Background campaign contract](controller-background-contract.md)
- [Performance facts and historical comparisons](performance-facts.md)
- [Historical benchmark registry](../profiling/benchmark-registry.md)
