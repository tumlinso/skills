

<!-- todo-orchestrator:v2-managed:start -->
# SK-AS1-OBSERVER-CONVERSATION: Persist and replay public observer tool conversation

Task revision: `956`; current project revision is in `todo-status.md`.

## Objective
Repair confirmed actual-model continuation nonprogress by replaying only public tool calls and packetized results as bounded conversation history, without hidden reasoning or semantic skill routing.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `validated`

## Next Action
Record actual accepted public tool-call JSON in observations and replay assistant call/user result conversation from durable checkpoints; bounded no hidden reasoning, no forced source rereads or routing policy. Qualify short actual read-answer before full paired journey.

## Ownership
- `exclusive`: `docs/as1-observer-conversation.md`
- `exclusive`: `local-coding-worker/local_worker/observer_runtime.py`
- `exclusive`: `tests/as1/test_sk_as1_observer_continuation.py`
- `exclusive`: `tests/as1/test_sk_as1_observer_conversation.py`
- `exclusive`: `tests/as1/test_sk_as1_observer_progress.py`
- `exclusive`: `tests/as1/test_sk_as1_runtime.py`
- `read`: `local-coding-worker/local_worker`
- `read`: `planning/adaptive-surface-v1`

## Dependencies
- `task`: `SK-AS1-OBSERVER-CONTINUATION`
<!-- todo-orchestrator:v2-managed:end -->
