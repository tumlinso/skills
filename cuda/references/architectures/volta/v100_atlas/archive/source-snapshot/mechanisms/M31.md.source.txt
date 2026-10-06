# M31 — Stream memory waits and writes

> Commands can coordinate work without a polling shader, subject to the submission graph.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** streams, semaphores, synchronization.
**Prerequisites:** R06 R09. **Evidence:** S17 S30 S42.

## Established substrate [A conditional; reachability C Driver API]

Driver API wait/write operations have memory type, capability and comparison restrictions. Their hidden memory dependencies are not automatically visible to CUDA scheduling. Managed pointers are excluded by the documented contract.

## Appropriation hypothesis

Use a phase counter as a compact inter operation surface and compare command waits to tiny poll/update kernels. Batch control commands when legal. This is a way to use an existing command actor rather than reserve SM work.

## Cost and rejection boundary

A wait can block its own producer. Preserve CUDA-visible ordering where needed. Cyclic comparisons need bounded counter distance;64-bit and remote flush support are queried separately. A legal comparison alone is not a visibility/progress proof.

## Next reads

Compositions: C22 C27. Experiments: E22 E15.
