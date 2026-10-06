# Scenario Formulas

## Activation-Heavy Dense Stage

Pattern:

- sparse early stage is fine
- dense projection happens
- activations dominate the budget

Best first moves:

- checkpoint selected dense blocks
- reduce microbatch only as much as needed
- recover throughput with accumulation

## Sparse-Staging-Heavy Pipeline

Pattern:

- multiple sparse formats or remap buffers exist simultaneously

Best first moves:

- shorten sparse intermediate lifetime
- remove duplicated formats
- move the sparse-to-dense boundary

## Optimizer-State-Heavy Training

Pattern:

- params and optimizer state dominate before activations do

Best first moves:

- reduce optimizer-state pressure if allowed
- avoid over-allocating persistent buffers

## Communication-Buffer Pressure

Pattern:

- multi-GPU buffers or workspaces meaningfully reduce usable batch size

Best first moves:

- scope buffers to the steady-state need
- reduce redundant staging
- re-check the chosen reduction structure

## Throughput Rule

The best fit strategy is the one that:

1. makes the job fit
2. preserves arithmetic intensity where possible
3. avoids moving the bottleneck from memory to host stalls or tiny batches
