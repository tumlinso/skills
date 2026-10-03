# M43 — NUMA-local host memory as a tier

> Align data production, page placement and GPU ingress.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** NUMA, PCIe, host memory, zero copy.
**Prerequisites:** R07 R08. **Evidence:** S30 S33 S36.

## Established substrate [A/D conditional; reachability C/OS]

Pinned/mapped host memory interacts with CPU placement, PCIe roots and IOMMU. Pinning does not necessarily make pages local. Mapped GPU access still traverses a transport with its own ordering contract.

## Appropriation hypothesis

Keep low bandwidth control or cold metadata in the appropriate host tier; stage hot payloads to HBM. Produced at a on the CPU side attached to the owning GPU to avoid unnecessary socket traffic.

## Cost and rejection boundary

Avoiding an extra CPU copy requires data already being local or produced there. It does not remove DMA. Verify actual roots and page placement; thread pinning alone is insufficient. Compare local, remote and simultaneous ingress.

## Next reads

Compositions: C23 C32. Experiments: E21 E35.
