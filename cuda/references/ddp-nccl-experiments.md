# NCCL Experiments Worth Running

## Minimal Experiment Set

1. baseline with defaults
2. verify the measured topology and peer paths
3. test the recommended rank ordering
4. only then test `NCCL_P2P_LEVEL` or algorithm/protocol restrictions

## What To Change Sparingly

- `NCCL_P2P_LEVEL`
- `NCCL_ALGO`
- `NCCL_PROTO`

Use them as experiments, not permanent defaults. NCCL’s own documentation warns that forcing environment variables can cause long-term performance problems or break future behavior if left set blindly.

## V100-Host-Specific Guidance

- `NVL` is useful to test strict pair-local behavior
- `PHB` is often the most informative cutoff on this host because it allows NVLink pairs and acceptable leader exchange while excluding the worst `SYS` paths
- if the default already performs best, keep it

## What To Record

- rank order used
- message sizes
- measured bandwidth and latency
- whether the tested override beats defaults consistently
