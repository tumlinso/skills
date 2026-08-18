# Distributed 4-GPU Planning

Use this reference to translate model choices into architecture choices for the 4x Tesla V100 host.

## Machine Assumptions

Assume:

- 4 GPUs
- 16 GB per GPU
- fast pair `0<->2`
- fast pair `1<->3`
- PCIe 3.0 is still the host-transfer bottleneck

## Default Planning Rules

- Make the model fit on one V100 first unless throughput or batch-size requirements clearly justify 4-GPU training.
- Prefer one process per GPU with DDP when the model replica fits per device.
- Treat activation-heavy models, long-context models, and diffusion as memory risks first.
- Treat small-step, communication-heavy designs as topology risks first.

## Family-Specific Implications

Autoencoders and VAEs:

- usually friendly to DDP if latent width and hidden size are controlled
- communication cost is often acceptable relative to compute

Temporal models:

- sequence length and saved activations often dominate memory
- plan windowing, truncated sequence training, or checkpointing early

Diffusion models:

- expensive in memory and wall time
- prefer latent diffusion, smaller backbones, and microbatching on V100
- do not assume 4 GPUs fixes a fundamentally over-wide model

Graph models:

- communication pressure depends on graph partitioning and batch construction
- pair-local data placement matters if neighbor exchange is frequent

Multimodal hybrids:

- encoder duplication can inflate memory
- keep modality towers narrow until the value of wider towers is proven

## Required Output

State:

- single-GPU first or 4-GPU by design
- likely memory limiter
- likely communication limiter
- whether `cuda` DDP or memory addendums should be consulted next
