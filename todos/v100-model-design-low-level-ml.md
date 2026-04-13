# Current Objective

## Summary
Extend `v100-model-design` so it can design low-level ML subsystems that may own forward, backward, optimizer, and trainer-loop logic outside Torch or libtorch when sparse or nonstandard layouts make framework overhead too expensive.

## Planning Notes
- The current skill stops at model family, distributed shaping, and custom-op boundary planning.
- The new route must stay at design level; `cuda-v100` remains the implementation and tuning handoff.
- Sparse and nonstandard-layout training paths are a primary motivator, but the route should still work for other layout-sensitive hot paths.

## Assumptions
- This is not a runtime-library skill. It is for deciding when ML-like code should be expressed at a lower level.
- Manual backward and optimizer ownership are first-class design decisions when framework overhead dominates.
- Most projects should still keep the rest of the model conventional unless the low-level path is clearly justified.

## Suggested Skills
- `v100-model-design` - Primary skill being extended.
- `todo-orchestrator` - Track the multi-step work in the shared ledger.
- `cuda-v100` - Downstream implementation and profiling handoff only after the design boundary is stable.

## Useful Reference Files
- `v100-model-design/references/route-custom-op-planning.md` - Existing boundary-planning route that needs to distinguish custom ops from broader low-level ML subsystems.
- `v100-model-design/references/model-family-selection.md` - Existing family-selection checklist that should expose framework ownership choices.
- `v100-model-design/references/bioinformatics-model-playbook.md` - Existing sparse and omics guidance that should route layout-heavy training cases into the new path.
- `v100-model-design/assets/custom_torch_ops.template.md` - Existing registry template that needs broader boundary and optimizer fields.

## Plan
- Add a new low-level ML boundary route to `v100-model-design/SKILL.md`.
- Create references for boundary routing, manual gradients, optimizer ownership, trainer loops, and sparse-layout training boundaries.
- Update the custom-op route, family-selection docs, bioinformatics playbook, registry convention, template, and metadata to expose the new path cleanly.
- Validate the updated skill and close the workstream.

## Tasks
- [x] Patch todo ledger for v100-model-design low-level ML workstream
- [x] Add low-level ML route to `v100-model-design/SKILL.md`
- [x] Create low-level ML reference set
- [x] Refresh existing references, template, and metadata
- [x] Validate skill and close ledger state

## Blockers
_None recorded yet._

## Progress Notes
- Initialized the v100-model-design low-level ML workstream and captured the intended design-level scope.
- Added `route-low-level-ml-boundary`, `manual-gradient-system-design`, `optimizer-and-update-design`, `low-level-trainer-loop-design`, and `sparse-layout-training-boundary`.
- Updated `SKILL.md`, the custom-op route, model-family references, bioinformatics playbook, registry convention, registry template, and OpenAI metadata to expose the new route.
- Validated the updated skill with repo-local checks: YAML parsing, front-matter parsing, description-length check, and referenced-file existence checks.

## Next Actions
- No immediate action; resume only if the user wants more concrete design examples or follow-on implementation work in `cuda-v100`.

## Done Criteria
- `v100-model-design` can distinguish ordinary custom-op planning from low-level ML subsystem planning.
- The skill can route questions about owned backward logic, optimizer ownership, and trainer-loop ownership into dedicated design docs.
- Sparse and nonstandard-layout training cases are explicitly represented as reasons to consider framework bypass.
- The skill still hands implementation and tuning work to `cuda-v100` rather than absorbing it.
