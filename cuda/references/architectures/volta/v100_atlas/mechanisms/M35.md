# M35 — Remote atomics and NVLink signaling

> Use a narrow control channel only after checking the exact pair and operation.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** NVLink, remote atomics, queues.
**Prerequisites:** R06 R07. **Evidence:** S02 S25 S30 S32.

## Established substrate [A/D conditional; reachability C/P]

Native peer atomic capability is per ordered pair and does not follow from a successful copy. The allowed operation, scope and allocation determine the actual contract.

## Appropriation hypothesis

Publish epochs, mailboxes and completion counts for owner-compute services. Batch many payload changes under one publication to keep control traffic small. Assign ownership so every data access need not be remote.

## Cost and rejection boundary

Polling itself consumes requests and owner service resources. Visibility, reuse and progress still need proofs. Provide termination if a peer stops. Compare events and command waits, including idle power and tail latency.

## Next reads

Compositions: C20 C22 C24. Experiments: E19 E15 E22.
