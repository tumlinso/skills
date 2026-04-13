# Model Family Selection

Use this reference to choose the model family before discussing implementation details.

## Decision Table

Choose a temporal model when the task is about:

- time evolution
- longitudinal response
- perturbation trajectories
- state transitions
- forecasting from ordered measurements

Good families:

- latent ODE or neural ODE models for continuous-time dynamics
- state-space or recurrent latent dynamics models for long or irregular sequences
- temporal transformers when sequence order matters and data volume supports them

Choose an autoencoder family when the task is about:

- latent compression
- denoising
- batch correction
- representation learning
- anomaly or reconstruction scoring

Good families:

- denoising autoencoders for robust embeddings
- variational autoencoders when a structured latent space matters
- conditional VAEs when labels, batches, or perturbations must control the latent space

Choose a diffusion family when the task is about:

- generative synthesis
- conditional generation
- iterative refinement
- strong-prior imputation

Use caution on V100:

- diffusion is usually heavier than a VAE or autoregressive baseline
- prefer latent diffusion over full-resolution diffusion when the raw state is large
- reject diffusion if the user only needs embeddings, simple denoising, or light conditional generation

Choose a graph model when the task is about:

- cell-cell neighborhoods
- regulatory or pathway interactions
- spatial adjacency
- relational message passing

Choose a transformer or sequence model when the task is about:

- ordered tokens or patches
- long-range dependencies
- large-context sequence conditioning

Choose a hybrid when the task needs multiple objectives, for example:

- VAE encoder plus temporal latent dynamics
- shared-latent multimodal encoder plus graph refinement
- autoencoder backbone plus diffusion in latent space

## Rejection Rules

- Reject diffusion if a VAE, denoising autoencoder, or conditional decoder already satisfies the objective.
- Reject a large transformer when the signal is mostly sparse tabular biology without meaningful sequence structure.
- Reject a static autoencoder for explicit time-evolution questions unless the temporal component is deliberately out of scope.
- Reject graph layers when the graph is weakly justified or mostly fabricated.

## Output Checklist

State:

- chosen family
- main alternative rejected
- objective being optimized
- expected memory and communication pressure
- whether the family is a good fit for Python-only, libtorch, both, or a selective low-level ML subsystem
- whether training should stay framework-managed, use a low-level hot component, or move most of the trainer below Torch or libtorch
