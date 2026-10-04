# Observer progress boundary

`ObserverWorkerPort` generates its command example from the command runner's
trusted startup roots. It advertises those permitted native roots in the system
instructions and chooses an existing allowed root for the example's `cwd`.
Caller `scope`, `hints`, and skill metadata describe an investigation; they never
grant mounts or override this policy. Adapters without root metadata receive an
example without `cwd`, allowing their own default. The example describes JSON
grammar; instructions explicitly require commands that advance the question.
The runner preserves trusted input root order while deduplicating resolved
paths, so the factory's project-first preference survives even for deeper
project directories. Granted mounts and credential masking are unchanged.

Ordinary step exhaustion returns `status: partial`,
`reason: step_budget_exhausted`, `authoritative: false`, all retained packetized
observations, and an unresolved question identifying the missing answer and
remaining verification. This terminal outcome must not schedule a continuation.
Real foreground preemption still returns `yielding/foreground_preemption` and
retains observations for a later fenced attempt. Session eviction still returns
`queued_after_eviction`. There is no global arbitrary retry limit.

The single JSON object parser, read-only tool allowlist, source-byte proofs,
credential masks, sandbox, stale-attempt fences, and agentic installed `SKILL.md`
navigation remain in force. No hidden reasoning is persisted.

## Source and evidence

Before editing, filesystem SHA256 of
`local-coding-worker/local_worker/observer_runtime.py` was
`99ebb05632b7768403e103bc32bb5f04885c86662272cef14bf83fb25e57ce8b` at
Git HEAD `e6c60f00fcc881681d791e750b5a43ca1f243a87`. Native task inspection
confirmed `SK-AS1-OBSERVER-PROGRESS` active at task/project revision 937.
No cached MCP file identity was used as source equivalence.
Final qualified module SHA256:
`0cb31c565e02a5aa524ba6cff8af0a35f94246385fac53d692260573e519336b`.

Executed producer regression command:

```sh
/home/tumlinson/project-control/.venv/bin/python -m pytest tests/as1/test_sk_as1_observer_progress.py -q
```

Result: 10 passed, including a separate child executing the nine behavior cases
against the exact actual source module path and parent-computed SHA256. The child
removes inherited release manifest/digest and runtime fingerprint pins, selects
the actual Skills root, and leaves the parent environment intact. Behavior
cases execute real Bubblewrap: parse and run the actual prompt example in an
allowed cwd, deny malicious caller roots, preserve exact source observations
across six command-only turns, preserve foreground yield/resume, fence stale
turns, reject multiple JSON objects and fences, and retain session eviction.
A rootless adapter separately exercises omission of `cwd`; a deeper project
root ordered before a shallower Skills root proves project preference and dedup.

The existing `tests/as1/test_sk_as1_runtime.py` was also executed in a separate
source-bound child with those deployment pins cleared and actual Skills/Todo/
compatibility import paths selected. Result: 19 passed and 11 subtests passed;
19 existing unregistered `as1_case` marker warnings. Current prerequisite
contracts assign RUN-01..03 to that file; RTM01..05 are absent. These regressions
cover native skill navigation, forbidden tools, command-time stale fences,
read-only mounts, scratch/network/device/credential exclusions, timeout cleanup,
byte bounds, warm-slot protocol, and native routing.

After the trusted ordering change, the final source-bound invocation ran both
files together with `-q`: 29 passed, 11 subtests passed, 19 existing marker
warnings in 2.89 seconds. Tool evidence is exec session `32032`, completion
chunk `e884d2`; final module SHA256 was confirmed in chunk `8a0d0b`.

These scripted protocol fixtures qualify changed producer behavior, not actual
Qwen inference or scientific results. Consumer broker normalization and exact
source pin qualification belong to Project Control's paired task. No GPU helper
or physical acceptance proof was changed or rerun; the root controls whether
prior physical evidence remains applicable. Unknown work, old failure evidence,
active parent environment and kernel, authority state, and AppleDouble files
were preserved. This worker does not commit or perform lifecycle acceptance.
