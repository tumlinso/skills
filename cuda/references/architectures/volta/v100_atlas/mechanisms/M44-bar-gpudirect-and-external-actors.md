# M44 — BAR, GPUDirect and external actors

> Reachable memory is not automatically an ordered shared protocol.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** BAR, GPUDirect, RDMA, PCIe.
**Prerequisites:** R07 R08 R06. **Evidence:** S33 S16 S30.

## Established substrate [A/D; reachability C/K/platform]

BAR mappings and peer registrations expose GPU memory under driver/platform rules. Aperture size is not necessarily total HBM or a permanent linear CPU view. External DMA has specific lifetime/ordering requirements.

## Appropriation hypothesis

An external actor can feed a GPU-owned pipeline or publish coarse work through a valid protocol. Studying registration/mapping also explains part of GPU peer addressing. Preserve explicit ownership at that boundary.

## Cost and rejection boundary

An external write visible in one domain need not be ordered before a running CUDA consumer. Root/IOMMU constraints and registration cost matter. A framebuffer mapping does not grant arbitrary MM IO/firmware control.

## Next reads

Compositions: C22 C23. Experiments: E21 E22 E35.
