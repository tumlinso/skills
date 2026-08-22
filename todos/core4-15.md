

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-15: Preserve backward compatibility and minimize all four skill surfaces

Task revision: `23`; current project revision is in `todo-status.md`.

## Objective
Remove private cross-skill imports, keep the three existing public workflows compatible, keep the new local-worker SKILL.md extremely small, correct root routing and ignore rules, add one repository validation entry point, and establish software-ready evidence without real model assets.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `integration_exclusive`
- Result: `-`

## Next Action
Update only public docs and compatibility adapters after the integrated flow works. Run the existing full suites once here, not during every prior task.

## Ownership
- `exclusive`: `.github/workflows/core4.yml`
- `exclusive`: `.gitignore`
- `exclusive`: `AGENTS.md`
- `exclusive`: `core4-tests/software-ready`
- `exclusive`: `cpp-context-compiler/SKILL.md`
- `exclusive`: `cpp-context-compiler/agents/openai.yaml`
- `exclusive`: `cuda/SKILL.md`
- `exclusive`: `cuda/agents/openai.yaml`
- `exclusive`: `local-coding-worker/SKILL.md`
- `exclusive`: `local-coding-worker/agents/openai.yaml`
- `exclusive`: `scripts/core4_validate.py`
- `exclusive`: `todo-orchestrator/SKILL.md`
- `exclusive`: `todo-orchestrator/agents/openai.yaml`
- `read`: `contracts`
- `read`: `cpp-context-compiler`
- `read`: `cuda`
- `read`: `local-coding-worker`
- `read`: `todo-orchestrator`

## Dependencies
- `checkpoint`: `CORE4-INTEGRATED-FLOW-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
