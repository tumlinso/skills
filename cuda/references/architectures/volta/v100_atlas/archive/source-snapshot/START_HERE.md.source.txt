# A00 — Start here — V100 software circuit-bending atlas

> A progressively disclosed machine reference, mechanism catalogue and experiment ledger for GV100/V100 SXM2.

**Status:** source-backed synthesis. **Depth:** 0.
**Read when:** entry point, model readability.
**Prerequisites:** none. **Evidence:** original synthesis; see linked mechanisms.


## Read only what changes the next decision

1. Search **NEED_INDEX.md** for the computational need. Read two or three mechanism cards, not the whole atlas.
2. Read a composition to obtain an explicit representation, equation, strong baseline and falsifier. Read R06 for concurrency, R15 for numerical reinterpretation, and R05 for tensor-fragment details.
3. Open a source capsule or experiment only when its guarantee, availability or uncertainty affects the choice.

```
python tools/read_atlas.py search "branchless sequence routing"
python tools/read_atlas.py read M01 M03 C01 --budget 1800 --refs
python tools/read_atlas.py read R05 C10 E09 --budget 2600
```

Budgets are words, not model-specific tokens. The reader emits complete cards or summaries with paths; it does not silently truncate correctness caveats. `--refs` shows prerequisite/source summaries without recursively dumping documents. The full compendium is for archival reading, not default model context.

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
