# Bounded skill-entry feedback

Before a successful exact installed `SKILL.md` source proof, skill mode permits
only direct `cat` argv for that validated canonical entry. Other proposed
commands or shared tools are denied **before dispatch**. Relative entry paths
are resolved against the proposed cwd; the existing runner still validates
cwd, mount access, limits and sandbox execution.

The runner's existing packetization path records actionable feedback:
`status: denied`, `reason: skill_entry_required`, `dispatched: false`, the exact
`required_skill_entry`, and a corrective instruction to read it successfully.
The denial contains no source-read proof or invented command output. Its actual
proposed tool/arguments remain `public_tool_call`; normal observation and
checkpoint handling then continue within the original step budget. The model
must choose the entry read and navigate the installed skill's maps itself.

Failed or truncated permitted entry reads are retained as their real command
observations. Their public continuation explains the unsatisfied prerequisite;
later calls remain blocked until a completed, exit-zero, nontruncated observation
provides exact entry path/hash proof. Final selection also requires that proof.
A resumed successful entry observation authorizes native reference reads without
forcing another entry read. Six refusals use six turns and terminate with the
existing `partial/step_budget_exhausted` outcome.

No internal retry, additional budget, implicit entry execution, fabricated model
call, semantic skill router, hidden reasoning, new mount, or tool grant was
added. Strict JSON, read-only allowlist, command sandbox, credential exclusions,
source validation, context/observation bounds, packet/checkpoint fences,
foreground preemption and eviction recovery remain in force.

## Qualification

Native inspection confirmed active `SK-AS1-OBSERVER-ENTRY` at revision 960,
depending on `SK-AS1-OBSERVER-CONVERSATION`. The prerequisite contract is
`local-coding-worker/references/observer-port.md`: the installed entry must be
the first successful skill read, and selected resources must be read by the
agent before selection. Existing broker source-order validation remains required.

Baseline commit: `34b7933fac3d39234388ba6adfb1cbe1fc2af943`.
Initial module SHA256:
`695981a69882c951487814425809659ec0abdccd428e329153a8acd6ce94d8e1`.
Final qualified module SHA256:
`8f19069f55b6f9e24b396c269f18a6c5eb7d162a7eef4880e530fdee045447dd`.
New test SHA256:
`3565d8e73f4808aed5970553b4d0346cd0ec22bbf92a0d0292447c7ccf58a9f9`.
The root and broker worker received the exact producer hash and denial contract.

A separate source-bound child removed inherited deployment manifest/digest and
runtime fingerprint pins, selected actual Skills/Todo/compatibility source paths,
and executed:

```sh
/home/tumlinson/project-control/.venv/bin/python -m pytest tests/as1/test_sk_as1_observer_entry.py tests/as1/test_sk_as1_observer_conversation.py tests/as1/test_sk_as1_observer_continuation.py tests/as1/test_sk_as1_observer_progress.py tests/as1/test_sk_as1_runtime.py -q
```

Result: **58 passed, 11 subtests passed**, 19 existing unregistered `as1_case`
marker warnings, in 3.44 seconds. Evidence: exec session `23896`, completion
chunk `e12938`; hashes and focused diff check in chunk `29ce4b`. Existing tests
required no edits. The ten new real-port/Bubblewrap cases cover a denied initial
find followed by model-chosen entry/resource/selection; six bounded refusals;
blocked semantic and downstream source calls; resumed entry proof without
reread; truncated/missing entry evidence blocking routes and finalization;
correction of a truncated read; fences before denial and during packet commit;
and relative direct-cat resolution to the canonical entry. An immutable denial
packet may survive supersession, but it cannot checkpoint into the new attempt.

Independent focused source review on the exact final hash returned no
consequential findings; the reviewer performed no tests. These CPU/scripted
regressions establish protocol/source behavior, not actual model inference.
The root owns installed candidate qualification, native gate completion and
integration. Only the assigned runtime, new test and this report were changed;
unknown work, projections, histories and AppleDouble files were preserved.
