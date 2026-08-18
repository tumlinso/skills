# Route: Distributed Shaping

Use this route when the model family is mostly known but the shape must be adapted to the 4x V100 host.

## Use When

- deciding whether to stay single-GPU first or design for 4 GPUs immediately
- constraining model width, depth, batch size, or modality packing
- evaluating whether distributed execution is a requirement or a premature complication

## First Move

Read `references/distributed-4gpu-planning.md`.

Classify the design as:

- single-GPU first
- 4-GPU by design
- dual-path prototype now, distributed later

## Load Next Only If

- return to `references/route-model-family.md` if the scaling discussion exposes a bad family choice
- switch to `references/route-custom-op-planning.md` if the design now depends on custom ops
- hand off to `cuda` when the remaining questions are memory fit, topology, or pipeline constraints

## Return To Root When

- the scaling posture is stable and the next uncertainty is custom-op scope or low-level implementation
