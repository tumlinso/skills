# Memory Accounting On V100 16GB

## Budget Categories

- parameters
- gradients
- optimizer state
- activations
- temporary workspaces
- communication buffers
- sparse intermediates
- staging buffers for host/device or sparse/dense transitions

## Rough Formulas

Use rough order-of-magnitude math first, then refine:

- parameter bytes = parameter_count * bytes_per_parameter
- gradient bytes = parameter_count * bytes_per_gradient
- optimizer bytes = parameter_count * optimizer_state_multiplier
- activation bytes = sum of retained intermediate tensors across the live forward/backward window

Treat sparse intermediates separately. A sparse pipeline can still blow memory through duplicated index/value structures or staged dense projections.

## Typical Pressure Patterns

### Parameters / Optimizer State Dominant

Common when:

- the model is simply too large
- optimizer state is heavy relative to params

Actions:

- reduce optimizer state pressure
- shard or stage more carefully
- revisit precision or optimizer choices if allowed

### Activations Dominant

Common when:

- batch or sequence dimensions are too large
- many intermediate tensors are retained

Actions:

- activation checkpointing
- microbatching with accumulation
- change the sparse-to-dense boundary if dense expansion happens too early
- verify the activations that are truly retained rather than assuming the whole forward footprint is live

### Sparse Intermediates Dominant

Common when:

- multiple sparse formats are kept alive at once
- remapping/filtering writes large transient structures

Actions:

- shorten sparse intermediate lifetime
- avoid over-conversion between formats
- fuse staging and follow-on work when possible
- do not keep CSR, CSC, dense projections, and remap buffers alive together unless reuse truly demands it

### Communication / Workspace Dominant

Common when:

- workspaces are oversized
- communication buffers stay allocated too broadly

Actions:

- shrink or scope workspaces
- separate setup from steady-state allocation
- benchmark the smaller-buffer variants

## Rule

Never say "the model does not fit" until the budget is broken into categories.

Then ask: which of those categories can be reduced without destroying throughput?
