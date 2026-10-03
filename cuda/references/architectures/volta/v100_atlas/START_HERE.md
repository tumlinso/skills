# A00 — Start here — V100 software circuit-bending atlas

> A progressively disclosed machine reference, mechanism catalogue and experiment ledger for GV100/V100 SXM2.

**Status:** source-backed synthesis. **Depth:** 0.
**Read when:** entry point, model readability.
**Prerequisites:** none. **Evidence:** original synthesis; see linked mechanisms.


## Read only what changes the next decision

1. Search **NEED_INDEX.md** for the computational need. Read two or three mechanism cards, not the whole atlas.
2. Read a composition to obtain an explicit representation, equation, strong baseline and falsifier. Read R06 for concurrency, R15 for numerical reinterpretation, and R05 for tensor-fragment details.
3. Open a source capsule or experiment only when its guarantee, availability or uncertainty affects the choice.

```python
skill_context(query="V100 branchless sequence routing", skill="<returned CUDA ID>")
skill_read(skill_id="<returned CUDA ID>", resource="<returned resource path>")
```

Use the returned resource paths to read the relevant mechanism, composition and prerequisite/source sections. The private reader is preserved in the original ZIP as historical authoring tooling; it is not the Project Control observer runtime. The full compendium is for explicit archival reading through `skill_read`, not default model context.

## Navigation surfaces

- **FIELD_GUIDE.md:** the representation-first performance reasoning and most unusual directions.
- **reference/R00–R15:** architecture, execution, memory, numerics, interfaces and limits.
- **mechanisms/M01–M52:** what a primitive does, what else it could do, cost and rejection gates.
- **compositions/C00–C39:** concrete original constructions; none has a measured V100 speedup here.
- **experiments/E00–E39:** falsifiable protocols, not forty completed GPU benchmarks.
- **sources/SOURCES.md:** primary sources with pinned versions where available, locators and short evidence capsules.
- **ledger/:** claims, hypotheses, scope, contradictions, unknowns, tests and append-only history.

## Evidence and access

A=ISA/API guarantee; D=NVIDIA implementation; E=original measurement; R=reverse engineering; H=reasoned hypothesis; S=speculation; U=unknown. Access: C=public CUDA/Driver API; P=PTX; B=binary; K=driver/channel; F=firmware/platform. These axes are independent. A documented command-engine field is not automatically a public interface.

The CPU semantic suite is included and run. No V100 kernel, latency, bandwidth, remote-cache behavior or novel speedup was measured in this session. The capability probe is provided as uncompiled source. Exact module wiring, electrical schematics, firmware contracts and several microarchitectural details remain explicit open questions.

The purpose is to widen the design space without replacing evidence by enthusiasm. No V200/meta-device implementation is selected. Updates are persistent files with a schema and maintenance protocol, not an autonomous background service.
