# Observer continuation contract

Every stateless observer turn receives the supplied question and retained public
observations, together with bounded public progress metadata: `stage`,
`observation_count`, and `remaining_steps`. Stage is `initial` when no observations
exist, `resumed` on an attempt's first turn with retained observations, and
`continuation` on later turns with observations. The worker stores no hidden
reasoning and reconstructs no private conversation.

Only the initial stage recommends starting with commands for relevant source,
files and Git. Continuation and resume explicitly instruct the model to review
retained observations, decide whether evidence is sufficient, and return final
JSON immediately if it is. Additional commands or shared tools remain available
for missing evidence. Incomplete, stale or otherwise unverified source evidence
may justify another read. Packet identity does not prove answer entailment.
These instructions guide a decision; they do not force an answer or route a
question semantically.

Skill mode's command example uses the actual validated installed `SKILL.md`
path and registered cwd. Retained exact entry observations satisfy the initial
entry requirement; the worker follows the installed entry's native maps and
references agentically. Final selected-resource byte verification remains
mandatory. The prompt advertises the runner's actual optional argument names:
`max_output_bytes` (integer 1..65536, default 8192) and `timeout_seconds`
(greater than zero, at most 60). The model chooses an adequate bounded limit;
truncated output does not prove full source. Existing 16384-byte observation
context omissions remain unchanged. The root measured the actual known
`cuda/SKILL.md` entry at 5005 bytes, so the default entry output bound fits;
there is no demonstrated entry-budget gap requiring read-proof changes.

Trusted mount roots, credential masks, packet/source proof rules, observation
count and request/context byte limits, stale-attempt fences, single JSON parsing,
read-only tool allowlist, foreground yield/resume, eviction recovery and terminal
`partial/step_budget_exhausted` behavior are unchanged.

## Qualified source and evidence

Native task inspection confirmed `SK-AS1-OBSERVER-CONTINUATION` active at project
revision 944, with prerequisite `SK-AS1-OBSERVER-PROGRESS`. Initial filesystem
module SHA256 was
`0cb31c565e02a5aa524ba6cff8af0a35f94246385fac53d692260573e519336b`
at Skills Git HEAD `769b53fd14d19dab3444d9961236105bc79d5c6d`.

Final qualified `local-coding-worker/local_worker/observer_runtime.py` SHA256:
`76f82d2ad6f0972df3c7016b60c30884fde72974fc1929fe029887541e935e3a`.
This exact hash was sent directly to the root and broker worker.

A separate source-bound child selected actual Skills/Todo/compatibility import
paths, removed inherited release manifest/digest and runtime fingerprint pins,
and executed:

```sh
/home/tumlinson/project-control/.venv/bin/python -m pytest tests/as1/test_sk_as1_observer_continuation.py tests/as1/test_sk_as1_observer_progress.py tests/as1/test_sk_as1_runtime.py -q
```

Final result: **36 passed, 11 subtests passed**, 19 existing unregistered
`as1_case` marker warnings, in 3.00 seconds. Evidence: exec session `9436`,
completion chunk `890424`; final hash and focused diff check in chunk `1e409b`.
The progress test also executes its own child against the parent-computed exact
module hash. The initial 36-test run passed before adding the root-requested
optional command-limit guidance; the final rerun qualified that changed source.

The seven new cases use the actual port and real Bubblewrap. They inspect
initial, continuation and resumed system/user contexts; read one source and
produce a packet-citing final answer without rereading it; resume retained
source after foreground preemption with fresh-attempt fencing; request missing
source when retained evidence is incomplete; read the exact skill entry and
follow its native router/reference files; reject multiple JSON objects and code
fences; and enforce the existing 24-observation input limit. Existing affected
29 cases cover sandbox, masks, source proofs, final skill verification, budget
exhaustion, eviction and native routing.

These are scripted protocol/source regressions, not actual Qwen inference or
scientific validation. The root owns subsequent installed candidate/model
qualification. This worker changed only its assigned runtime, new regression
file and this report; no commits, native lifecycle/authority changes, GPU work,
new mounts/tools, or unknown source/history cleanup occurred.
