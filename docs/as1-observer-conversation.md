# Public observer conversation ledger

Each accepted model tool call is preserved as `public_tool_call` on its
packetized observation. This field contains exactly the parsed public
`tool` and `arguments` object, copied before dispatch so adapter mutation cannot
rewrite the accepted call. Checkpoint and terminal/yield results preserve that
metadata with the observed packet. Raw model output and hidden reasoning are
not stored. Tool results cannot inject or overwrite the call field.

Every bounded stateless turn reconstructs the conversation:

1. Stable read-only system protocol, including allowed roots and exact skill
   entry example.
2. Initial user question/scope/hints/skill once, without duplicating observations.
3. For each observation with accepted-call metadata, assistant call JSON then
   user packetized result JSON. The result excludes the call metadata to avoid
   duplication.
4. A final user continuation/progress message without the original question or
   tool-first examples. It asks the model to judge sufficiency and answer, or
   obtain missing evidence.

The first turn without observations has only system/user messages and initial
public progress. On resume, the durable observation ledger produces the same
assistant-call/user-result history. Legacy observations and internal final
skill-validation reads have no accepted model call; they remain explicit user
`retained_observation` messages. No call is fabricated for them. Retained calls
are checked for the same allowed tool names and exact public JSON shape.

The full encoded turn, including system/history/continuation/session metadata,
is limited to 60000 bytes. Retained observations remain capped at 24. New
observation context remains bounded to 16384 bytes including its accepted call:
oversized result bodies become honest packet-ID/omission excerpts, preserving
the exact call. Calls unable to fit the bounded observation metadata are rejected
before dispatch; the final excerpt size is checked too. Packet proofs are not
invented for omitted payloads. Source proofs, initial entry requirements,
agentic native skill references and final exact-byte selection verification are
unchanged. Model sufficiency remains a decision, not a forced final or routing
rule.

Strict single JSON parsing, tool allowlist, mount/credential sandbox policy,
fences, foreground preemption, eviction recovery and terminal
`partial/step_budget_exhausted` behavior remain in force. No model retry counter,
canned answer, semantic router, broad mount, new tool or hidden conversation was
introduced.

## Source and qualified evidence

Initial native task inspection found `SK-AS1-OBSERVER-CONVERSATION` active at
revision 951, depending on `SK-AS1-OBSERVER-CONTINUATION`. The root's supported
scope/claim amendments at revisions 952 and 953 added precise migration of the
prior continuation/progress/runtime tests. Initial module filesystem SHA256:
`76f82d2ad6f0972df3c7016b60c30884fde72974fc1929fe029887541e935e3a`.
Git baseline: `21be127240c4fd91616a26c5ce1c1ada6aed23df`.

Final qualified module SHA256:
`695981a69882c951487814425809659ec0abdccd428e329153a8acd6ce94d8e1`.
This hash was sent to the root and broker worker for exact consumer binding.

A source-bound child cleared inherited deployment manifest/digest and runtime
fingerprint pins, selected actual Skills/Todo/compatibility import paths, and ran:

```sh
/home/tumlinson/project-control/.venv/bin/python -m pytest tests/as1/test_sk_as1_observer_conversation.py tests/as1/test_sk_as1_observer_continuation.py tests/as1/test_sk_as1_observer_progress.py tests/as1/test_sk_as1_runtime.py -q
```

Final result: **48 passed, 11 subtests passed**, 19 existing unregistered
`as1_case` marker warnings, in 3.20 seconds. Evidence: exec session `65962`,
completion chunk `776ec0`; source/test hashes and scoped diff check in chunk
`12a61b`. The initial migrated-suite invocation passed 47 cases. A further
accepted-call integrity case addressed a risk identified by static inspection:
adapter mutation could change the stored call unless copied before dispatch;
this case and that fix were included
in the final 48-case qualification.

The twelve new cases inspect actual initial two-message and continued
assistant/user history; require actual prior calls plus real Bubblewrap source
results before a scripted backend can answer; verify checkpointed replay after
foreground preemption and fencing; preserve legacy evidence without fake calls;
allow missing-evidence commands; replay exact installed skill entry/native
reference calls before selection; bound full transcript bytes; preserve calls
when payloads require omission; reject multi-JSON and code fences; fence stale
turns; reject unavailable tools in retained metadata; and prevent adapter
argument mutation from rewriting the public ledger. Existing continuation and
progress assertions moved source checks from the deliberately nonduplicated
initial user message into actual replayed result messages, preserving stdout,
packet identity, source proofs and preemption/resume requirements. The runtime
file required no source changes.

Changed files: `local-coding-worker/local_worker/observer_runtime.py`,
`tests/as1/test_sk_as1_observer_conversation.py`,
`tests/as1/test_sk_as1_observer_continuation.py`,
`tests/as1/test_sk_as1_observer_progress.py`, and this report.
No commit, native authority/lifecycle, GPU, kernel, or unknown-source changes
were performed. These are scripted protocol/source tests; actual inference and
short read-answer preflight remain root-owned before full paired qualification.
