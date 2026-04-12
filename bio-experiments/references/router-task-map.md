# Task Router

Read this file after selecting the assay reference. Then load only one task branch unless the request clearly spans phases.

## Choose One Branch

- preprocessing pipeline -> `task-preprocessing.md`
- dataset merge, cross-study alignment, metadata cleanup, feature alignment -> `task-dataset-unification.md`
- batch correction, harmonization, shared latent space, anchor mapping, multimodal alignment -> `task-integration.md`
- tensor preparation, sparse matrix construction, split generation, model-ready features -> `task-model-inputs.md`

Load `hard-constraints.md` in addition to the branch file when:

- data from more than one study, donor, batch, chemistry, or modality will be combined
- normalization state is unknown or mixed
- the task converts processed data into tensors or train and validation sets
- the request asks for integration or harmonization

## Quick Routing Rules

- If the request says "build a pipeline", start with `task-preprocessing.md`.
- If the request says "merge", "standardize", or "unify", start with `task-dataset-unification.md`.
- If the request says "integrate", "correct batch", or "harmonize", start with `task-integration.md`.
- If the request says "prepare for training", "construct inputs", or "export tensors", start with `task-model-inputs.md`.

Return to the assay file if any step changes feature definitions, matrix orientation, or modality meaning.
