# Broker-facing observer port

`local_worker.observer_runtime.ObserverWorkerPort` reuses
`ProductionBackend.run_observer_turn`, including checked installed model policy,
resource admission and warm slots. It adds no daemon, queue, scheduler, download,
network fallback or durable database. The broker must dispatch committed jobs
independently of MCP request lifetime and preserve observations after eviction.

Construct `ReadOnlyCommandRunner(roots, packetize=..., credential_paths=...)`
with trusted registered roots and credential exclusions. Never derive mounts
from a model response. Commands take argv, cwd, timeout and byte limits, and
run in Bubblewrap with read-only mounts, private process/network namespaces,
cleared environment, dropped capabilities, masked credentials and synthetic
devices. Scratch is disposable. Output is bounded while pipes are drained;
timeout and completion clean up the process group. A missing sandbox or failed
packet commit returns an honest failure. Packetization is supplied by the broker.
Command provenance is explicitly coarse and volatile, including observations
outside a nominated project. Do not infer exact file dependencies from argv.

Construct `ObserverWorkerPort(backend, command=..., tools=..., fence=...,
checkpoint=...)`. `tools(name, arguments)` returns a packetized read-only shared
tool result; it must use the investigator policy and broker storage, never a
coder/mutator profile. Allowed tools are command, log, overview, delta, frontier,
search, evidence, impact, history and machine. Recursive investigate/skill,
read adapters, child delegation, task claims and mutation are denied before
the callback. Machine diagnostics use fixed broker adapters, never device mounts.

`run(request)` accepts job_id, positive attempt, mode (`investigate` or `skill`),
question, optional scope/hints/observations, max_steps (1..12), session_id and
existing compute_profile/parallelism. Skill requests include a broker-registered
`skill={name,root}` constrained to the runner's trusted mounts. No whole-project
overview, instruction files, or previous caller context is automatically added.
Skill mode prompts the agent to read installed SKILL.md and traverse its own
maps/references; indexes remain advisory. Final selections are checked against
sandbox-observed resource hashes and line ranges within the registered root.
The installed entry must be the first successful skill read, and every selected
resource must have been read by the agent before its final answer. Direct
`cat` argv reads record exact path, hash and line count in the command packet;
other commands retain coarse provenance. A verifier read cannot substitute for
agent navigation. Verification rereads only to check freshness and ranges.

The result echoes job_id and attempt and has status completed, partial, yielding,
queued_after_eviction or stale_attempt. Results contain compact findings,
observations and unresolved questions; skill results include a source selection.
Resume using job-owned observations, not hidden reasoning or opaque KV state.
Explicit supervisor session leases may be shared for warm model reuse because
each turn sends independent explicit messages. No transcript is kept on the port.

`fence(job_id, attempt)` must check the broker's current generation. It is checked
before and after inference/tools and before packetization/checkpoint. Checkpoint
and final broker commits must ALSO perform atomic generation checks in their own
transaction: a Python callback check cannot close a transaction race. Late
attempts return stale_attempt without publishing model answers. An immutable
packet created just before eviction may survive, but cannot update a new attempt.
Checkpoint receives observed evidence only. Disconnects and lease expiry belong
to broker lifecycle; this synchronous port never cancels an accepted durable job.

Existing coding delegation/collection remains functional through internal kernel
APIs. The compatibility MCP's native routing wrapper excludes those handlers
from tool listings and rejects dispatch with `temporarily_inactive`. The canonical
kernel server and methods remain unchanged for explicit maintenance and tests.
This guard covers the Skills-owned compatibility fallback entrypoint selected
when the current Project Control CLI is absent. The preferred installed Project
Control CLI still receives the original `serve codex` forwarding call. Its native
profile discovery/dispatch and deployed startup are a PC-SURFACE consumer
requirement, followed by end-to-end API-03/API-04 and paired SQA validation; this
worker source change does not claim those producer/deployment checks passed.

Scripted model transports and supervisor fixtures establish protocol behavior,
not inference. Qualification must separately exercise the installed verified
model under the host CUDA interlock and demonstrate useful evidence-backed
answers and skill selections. GPU launches require coordinated admission.
