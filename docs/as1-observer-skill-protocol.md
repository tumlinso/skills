# Skill final protocol and bounded corrective feedback

Skill mode now presents one complete mode-specific final JSON example:
`answer`, `findings`, `unresolved_questions`, and `skill_selection`, containing
`format`, `selections` (`skill`, `resource`, `content_sha256`, `line_start`,
`line_end`, `reason`), `synthesis`, and `unresolved`. Investigate mode retains its
ordinary final grammar. Example values describe grammar, not source evidence;
the model must choose relevant native resources, copy their observed hashes and
valid ranges, and follow installed skill maps. Indexes remain advisory.

Parsed but malformed or unverified skill finals become packetized feedback:
`status: denied`, `reason: skill_final_validation_failed`, `validation_error`,
`accepted: false`, and explicitly labelled
`validation_data: {proposed_final, is_source_evidence: false}`. The proposed
payload is preserved truthfully as rejected validation data, not accepted
findings, a synthesized selection, an executed command, or a fabricated public
tool call. A corrective instruction identifies complete final grammar and the
need to read missing/truncated selected files with adequate `max_output_bytes`.
Normal observation/checkpoint handling lets the model correct its response using
retained evidence and the same remaining step budget. Repeated refusal still
ends in terminal `partial/step_budget_exhausted`.

Strict single-object parsing remains unchanged: multiple JSON objects and code
fences are not repaired or retried. Source hashes, line/range checks, entry-first
requirements, final exact-byte verification, roots, sandbox policy, fences,
preemption, model-output limits and tool permissions remain in force. There are
no extra model steps, hidden retries, new resource auto-reads or semantic routing.

A focused review found that rejected-final packet IDs could otherwise be used
to support a later invented finding. Accepted finding references now exclude
explicit non-source validation data and denied/undispatched entry-policy packets,
including retained packets after resume. Entry denial explicitly carries
`accepted: false` and `dispatched: false`. Legitimate failed command observations
remain eligible as evidence of factual failure. Inability can be reported in
unresolved questions without treating rejected proposals as source facts.

## Proven observation boundary

Root's exact Q10 guide metadata: 16142 bytes, 456 lines, SHA256
`9816ac78e6ccb23b8ca575219cb60d68699a6e5f2ae24e3c089fb922e2b04f24`.
The default 8192-byte cat output was truncated and supplied no full source proof.
Even a complete guide exceeded the old 16384-byte observation ceiling: escaped
newlines alone push JSON body size past it, before other packet metadata.

The authorized per-observation ceiling is now **32768 bytes**, including public
call metadata. A model-chosen bounded full read of this guide size retains stdout
and exact `source_reads`. Larger results remain honest omission excerpts without
full-body/source-proof claims. This does not guarantee arbitrary files can be
selected: a full source observation beyond this ceiling or a transcript beyond
60000 bytes remains an explicit limitation; source verification is not relaxed.
The serialized whole-turn limit remains 60000 bytes, request limit 65536 bytes,
observation count 24, command output cap 65536 bytes, and model output 16384 bytes.

## Qualified source and evidence

Native inspection confirmed root `SK-AS1-QUALIFY` active at revision 966.
Baseline commit: `9d19b348ca3630442bf6368e95e3e5a79865afa6`.
Initial observer module SHA256:
`8f19069f55b6f9e24b396c269f18a6c5eb7d162a7eef4880e530fdee045447dd`.
Final qualified observer module SHA256:
`ac6b0eca766863617bdeed4257e690fb89ce583cdb4199328e8234f42cff09bf`.
Root, paired head and broker worker received that exact hash and contract.

A source-bound child cleared inherited deployment manifest/digest and runtime
fingerprint pins, selected actual Skills/Todo/compatibility source paths, and ran
all six files with `-q`:
`test_sk_as1_observer_skill_protocol.py`, `test_sk_as1_observer_entry.py`,
`test_sk_as1_observer_conversation.py`, `test_sk_as1_observer_continuation.py`,
`test_sk_as1_observer_progress.py`, and `test_sk_as1_runtime.py`, under `tests/as1`.
The affected suite passed 67 tests and 11 subtests in 3.85 seconds, with 19 existing
unregistered `as1_case` marker warnings (session `78473`, chunk `dce84a`).

After root requested entry-denial exclusion as well, only the three affected
finding-reference cases were repeated against the final source:

```sh
/home/tumlinson/project-control/.venv/bin/python -m pytest tests/as1/test_sk_as1_observer_skill_protocol.py -q -k 'rejected_final_packet or entry_denial_packet or failed_command_packet'
```

Result: 3 passed, 8 deselected, in 0.16 seconds; final hash and proof in chunk
`ef5b53`. Independent source review verified the finding resolved on that exact
final hash and found no further issue in its bounded resolution scope.

The eleven new cases cover mode-specific grammar; missing-selection final then
corrected final; unread-resource rejection before any verifier read; exact Q10-
sized truncated guide then model-chosen complete read with retained bytes/hash;
six bounded malformed finals; supersession before feedback and during packet
commit; strict multiple-JSON rejection; rejected-final and entry-denial citation
laundering after resume; and preserved failed-command factual evidence. The
original suite ran before and after the initial reviewer finding fix. Existing
fixtures were changed only for the now-corrective invalid-final outcome and the
new >32 KiB omission boundary, preserving their negative source-proof assertions.

These are CPU/scripted protocol/source tests, not actual model inference. The
root owns the next installed candidate/actual skill journey, native lifecycle
and final integration. No live authority, GPU, hidden state or unknown-source
cleanup was performed. Product delivery includes only this report, the runtime,
the new regression file, and the three genuinely affected existing test files.
