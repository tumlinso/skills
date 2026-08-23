# Local worker resource policy

`AdapterService` resource coordination is opt-in. Construct it with a host
resource coordinator and project root, then include `resource_request` in the
start context. Existing contexts and adapter lifecycle calls behave unchanged.

A service starts as active local delegation and becomes idle model residency
after startup and between runs. While a bounded run is executing it is promoted
to active local delegation. A host preemption signal is handled cooperatively by the service heartbeat:
the adapter is drained, evicted, and its physical lease is released. A request
that has not started returns `NEEDS_CODEX`; completed adapter output is retained
if eviction arrives after the run. Todo task and evidence state are never owned
or modified by this service layer.

Resource acquisition does not download a model or start an adapter until the
runtime-discovered bundle is actually reserved. There are no recursive agents
and no hard-coded GPU indices or topology assumptions.

`CORE4-MODEL-SERVICE/2` profiles bind a verified model hash to the runtime
allocation and llama.cpp launch settings. GPU UUIDs are supplied through
`CUDA_VISIBLE_DEVICES`; supported server flags are detected once from the
installed binary. Startup is health-gated, output is retained at the declared
log path, eviction terminates the process group, and bounded idle TTL plus
`wait_for_quiescence` make VRAM release observable.
