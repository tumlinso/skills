# Benchmark Interpretation

## If `0,2` Or `1,3` Strongly Beats Adjacent Ordinals

Interpret as:

- the workload is respecting the real NVLink pairs

Action:

- lock rank order or visible device mapping to preserve the good pairing

## If 4-GPU Scaling Is Much Worse Than 2-GPU Scaling

Interpret as:

- cross-pair communication is likely too heavy
- the reduction structure may be too flat

Action:

- move to pair-local-first hierarchy
- reduce or summarize traffic before cross-pair exchange

## If Default NCCL Beats Forced Env Vars

Interpret as:

- the hand-tuned override is unnecessary or harmful

Action:

- keep defaults
- only retain overrides that win repeatedly at relevant message sizes

## If Small Messages Behave Differently From Large Messages

Interpret as:

- algorithm and protocol effects are message-size sensitive

Action:

- benchmark at the actual message sizes of the training loop
- do not generalize from one microbenchmark point

## If CPU Changes Move Communication Results

Interpret as:

- host placement or launch structure is contaminating the result

Action:

- revisit CPU affinity
- confirm one process per GPU
- separate host bottlenecks from true NCCL topology effects
