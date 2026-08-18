# Large-Data Benchmark Saturation On V100

Use this reference when the benchmark already has a standard summary contract, but the large-data cases are not strong enough to actually saturate compute, transfers, or collectives on Tesla V100 16 GB `sm_70`.

The main rule is:

- `small` is for smoke
- `large-compute` is for sustained compute saturation
- `large-transfer` is for sustained transfer, staging, or communication pressure
- `real` is for representativeness

Do not collapse `large-compute` and `large-transfer` into one vague `large` bucket.

## 1. Large Variants

### `large-compute`

Use this when the goal is to keep the hot kernels active long enough to expose the real compute ceiling.

A good `large-compute` case:

- has a clear steady-state window
- produces repeated hot kernels rather than one short burst
- avoids launch-noise-dominated conclusions
- is large enough that Tensor Core-eligible dense work can show its real path
- records the counters needed to explain throughput

### `large-transfer`

Use this when the goal is to expose host staging, PCIe copies, NVLink movement, or collective cost.

A good `large-transfer` case:

- preserves realistic copy granularity, shard movement, or reduction volume
- makes H2D, D2H, or collective phases visible in the summaries
- avoids tiny toy transfers that disappear into measurement noise
- keeps the compute phase present enough to show whether overlap exists or fails

## 2. Saturation Rules

Treat a `large` case as valid only when:

- warmup is outside the measured window
- steady-state iterations are repeated
- the measured phase lasts long enough to drown out launch setup noise
- the summary clearly states whether the case is compute-dominant, transfer-dominant, or mixed
- the placement and visible devices are recorded for this exact V100 host

For 4-GPU cases, preserve the real fast pairs `0<->2` and `1<->3`. Do not design a stress benchmark that accidentally measures the wrong topology.

## 3. Designing `large-compute`

Prefer `large-compute` shapes that:

- create repeated hot kernels on all intended GPUs
- use Tensor Core-friendly blocking or padding when the real workload is dense or reformulable
- amortize one-time layout conversion or packing outside the measured loop when the steady-state application would do the same
- avoid tiny batched work that leaves the SMs underfed

For dense or blocked Tensor Core-eligible paths:

- use FP16 inputs when numerically acceptable
- make important dimensions multiples of 8
- batch or group small work into larger matmul-shaped launches
- keep the hot data resident on-device during the measured loop

If a dense `large-compute` case stays far below expected throughput, utilization, or board power, route into Tensor Core validation before polishing micro-details.

## 4. Designing `large-transfer`

Prefer `large-transfer` cases that:

- preserve real host staging, sharding, or reduction behavior
- keep transfer batch sizes large enough to show PCIe or NVLink reality
- separate one-time setup from repeated steady-state copies or collectives
- make overlap failure visible instead of hiding copies behind one giant untimed setup step

Use `large-transfer` when the workflow is limited by:

- pinned-memory behavior
- copy fragmentation
- host collation or staging
- sharded exchange
- all-reduce or reduce-scatter volume

Do not label a benchmark `large-transfer` if almost all measured time is actually spent inside one kernel.

## 5. Summary Contract Additions

Every large-data summary should state:

- `scenario_kind: large-compute | large-transfer`
- whether the measured window is compute-dominant, transfer-dominant, or mixed
- what phase dominated wall time
- whether the case is intended to stress Tensor Core saturation, PCIe pressure, NVLink pressure, collective pressure, or glue-heavy steady state
- whether the run kept data resident on-device during the measured loop

## 6. Power And Utilization Interpretation

For eligible dense `large-compute` runs, high sustained board power is expected and useful supporting evidence that the Tensor Core path is alive.

Do not use power alone as the verdict.

Interpretation rules:

- high power plus weak throughput can still mean the kernel structure is wrong
- low power on a dense Tensor Core-eligible run is a sign to check dtype, blocking, batching, padding, and library selection
- low power on a transfer-bound case is not a failure

## 7. Output Requirements

Be explicit about:

- whether the scenario is `large-compute` or `large-transfer`
- whether the measured loop is representative of real steady state
- what was sized to create saturation
- whether the case is intended to stress compute, transfers, collectives, or glue
- whether the path should route into Tensor Core guidance, pipeline guidance, topology guidance, or roofline tuning next
