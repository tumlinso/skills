# V100 / SXM2 Software Circuit-Bending Atlas

**Research/synthesis date:** 2026-10-03. **Edition:** 1.0.

This is the archival all-in-one view. For selective model context, use START_HERE.md, NEED_INDEX.md and tools/read_atlas.py in the ZIP package.

Evidence, original hypotheses and unresolved details remain separately labeled. No GPU timings, CUDA compilation or novel speedups were measured during authoring.

## Contents

- [A00 — Start here — V100 software circuit-bending atlas](#a00)

- [A01 — Index by computational need](#a01)

- [A02 — Performance field guide](#a02)

- [R00 — Reading and evidence contract](#r00)

- [R01 — Machine reference](#r01)

- [R02 — Execution, scoreboards and operands](#r02)

- [R03 — Memory as algorithmic structure](#r03)

- [R04 — ISA families and generation traps](#r04)

- [R05 — Tensor geometry and native register interfaces](#r05)

- [R06 — Participation, visibility and progress](#r06)

- [R07 — NVLink, PCIe and NUMA as information boundaries](#r07)

- [R08 — Virtual memory, ATS and faults](#r08)

- [R09 — The non-SM command machine](#r09)

- [R10 — toolchain and binary evidence](#r10)

- [R11 — Performance model for circuit bending](#r11)

- [R12 — Measurement discipline and obs er v ability](#r12)

- [R13 — Electrical, firmware and reliability frontier](#r13)

- [R14 — Composition, conflict and scope map](#r14)

- [R15 — Numerical contracts for unconventional arithmetic](#r15)

- [M01 — LOP3 as a bank of Boolean circuits](#m01)

- [M02 — Mask rank/select as routing](#m02)

- [M03 — PRMT as a tiny register lookup](#m03)

- [M04 — Shuffle as a constrained routing fabric](#m04)

- [M05 — Match as an ephemeral associative table](#m05)

- [M06 — Ballot transpose and bit-sliced state](#m06)

- [M07 — Predicates and reconvergence as data representation](#m07)

- [M08 — DP4A/DP2A as structural arithmetic](#m08)

- [M09 — Packed SIMD and conversions as state operators](#m09)

- [M10 — S F Us and interpolation as alternate arithmetic](#m10)

- [M11 — FP64 and wide integer paths as alternate resources](#m11)

- [M12 — Register banks as an operand-delivery circuit](#m12)

- [M13 — Operand reuse and dependency control](#m13)

- [M14 — Register-resident local state machines](#m14)

- [M15 — Warp and SM specialization](#m15)

- [M16 — Instruction-level parallelism and useful overlap](#m16)

- [M17 — Instruction cache and phase factoring](#m17)

- [M18 — Shared memory as a banked routing network](#m18)

- [M19 — Barriers as phase boundaries](#m19)

- [M20 — L1, local memory and deliberate cold spills](#m20)

- [M21 — L2 as a compact coordination service](#m21)

- [M22 — HBM and coalescing as layout constraints](#m22)

- [M23 — Constant and texture paths as function interfaces](#m23)

- [M24 — Four native tensor microcircuits per warp](#m24)

- [M25 — Fragment-native intermediates](#m25)

- [M26 — Tensor counting and reduction](#m26)

- [M27 — Tensor transforms and state mixers](#m27)

- [M28 — Mixed precision and certified decisions](#m28)

- [M29 — Atomics as merge algebra and state transitions](#m29)

- [M30 — Persistent queues and resident interpreters](#m30)

- [M31 — Stream memory waits and writes](#m31)

- [M32 — Cooperative grids and historical multidevice launch](#m32)

- [M33 — Graphs and device-side launches](#m33)

- [M34 — Peer loads as a distributed data path](#m34)

- [M35 — Remote atomics and NVLink signaling](#m35)

- [M36 — Copy engines as asynchronous workers](#m36)

- [M37 — Copy-engine component remapping](#m37)

- [M38 — semaphore arithmetic outside SM execution](#m38)

- [M39 — QMD as a control object](#m39)

- [M40 — VMM views and virtual contiguity](#m40)

- [M41 — ATS and fault replay as coarse policy machinery](#m41)

- [M42 — Access counters as delayed feedback](#m42)

- [M43 — NUMA-local host memory as a tier](#m43)

- [M44 — BAR, GPUDirect and external actors](#m44)

- [M45 — Contexts, IPC and MPS](#m45)

- [M46 — Counters as runtime feedback](#m46)

- [M47 — Special registers and local clocks](#m47)

- [M48 — Cubin and SASS transformation](#m48)

- [M49 — Embedded processors and firmware frontier](#m49)

- [M50 — Graphics, media and dormant engines](#m50)

- [M51 — Faults, reset and RAS](#m51)

- [M52 — Power and thermal budgets as resources](#m52)

- [C00 — Bit-sliced full adders and arbitrary local Boolean rules](#c00)

- [C01 — Sequence symbols as two-plane equality circuits](#c01)

- [C02 — Ballot transpose as a persistent state encoding](#c02)

- [C03 — A warp-resident byte lookup network](#c03)

- [C04 — Warp CAM plus one reservation per equal destination](#c04)

- [C05 — A32-vertex graph carried in warp registers](#c05)

- [C06 — A bit-sliced finite-state engine](#c06)

- [C07 — Guard-digit convolution using ordinary integer multiplication](#c07)

- [C08 — Packed integer scores instead of float bookkeeping](#c08)

- [C09 — Exact bounded integers on the FP64 path](#c09)

- [C10 — Four tiny linear machines in one MMA warp](#c10)

- [C11 — Tensor cores as common-neighbor counters](#c11)

- [C12 — Prefix and reductions by structured matrices](#c12)

- [C13 — Fixed transforms as configurable tensor circuits](#c13)

- [C14 — Certified approximate screening with exact refinement](#c14)

- [C15 — High/low precision expansion as a composite operator](#c15)

- [C16 — Cancel intermediate transposes by composing ownership maps](#c16)

- [C17 — Operand-read hypergraph coloring](#c17)

- [C18 — A portfolio of useful pipeline work](#c18)

- [C19 — Manual latency hiding without importing cp.async](#c19)

- [C20 — Owner-compute instead of remote pointer chasing](#c20)

- [C21 — Transmit support or deltas instead of dense state](#c21)

- [C22 — A published ring with explicit reuse epochs](#c22)

- [C23 — Topology-aware ownership and dual host ingress](#c23)

- [C24 — Monotone atomic fixed-point computation](#c24)

- [C25 — A resident micro service with a finite operator palette](#c25)

- [C26 — Component remapping in the copy engine](#c26)

- [C27 — Command-engine completion arithmetic](#c27)

- [C28 — Dependent QMDs as a bounded dataflow experiment](#c28)

- [C29 — A doubled virtual ring without duplicate payload](#c29)

- [C30 — Translation-policy zoning on an ATS platform](#c30)

- [C31 — Texture interpolation as a nonlinear circuit element](#c31)

- [C32 — A coarse self-adapting kernel policy](#c32)

- [C33 — Steady-state scheduling under power and thermal limits](#c33)

- [C34 — Phase-factored circuits instead of a giant mega kernel](#c34)

- [C35 — Delete metadata through positional identity](#c35)

- [C36 — Compose lane, bank and fragment permutations](#c36)

- [C37 — Carry-save trees for bitset threshold queries](#c37)

- [C38 — Empirical conflict maps as placement hints](#c38)

- [C39 — A representation-changing search procedure](#c39)

- [E00 — Inventory and capability gates](#e00)

- [E01 — Algebra and encoding checks](#e01)

- [E02 — Instruction latency versus throughput](#e02)

- [E03 — Cross-pipeline interference](#e03)

- [E04 — Register bank and operand-reuse effects](#e04)

- [E05 — Warp routing, matching and lookup](#e05)

- [E06 — Shared banks and phase pipelines](#e06)

- [E07 — Cache and transaction accounting](#e07)

- [E08 — Translation working sets and pages](#e08)

- [E09 — MMA lane and register ownership](#e09)

- [E10 — Tensor numerical fingerprint](#e10)

- [E11 — Tensor versus bitset intersections](#e11)

- [E12 — Tensor circuits versus structured SIMT](#e12)

- [E13 — Representation crossover](#e13)

- [E14 — Atomics as useful coordination](#e14)

- [E15 — Publication and progress litmus](#e15)

- [E16 — Persistent roles and residency](#e16)

- [E17 — DMA and compute overlap](#e17)

- [E18 — Peer loads, cache behavior and latency](#e18)

- [E19 — Peer signaling and clock relationships](#e19)

- [E20 — Actual NVLink routing and saturation](#e20)

- [E21 — Host NUMA ingress](#e21)

- [E22 — Stream memory operations](#e22)

- [E23 — VMM alias and view behavior](#e23)

- [E24 — Fault and access-counter policy](#e24)

- [E25 — Feedback cost and regret](#e25)

- [E26 — Texture and SFU approximation](#e26)

- [E27 — Copy remap reachability](#e27)

- [E28 — Copy-engine semaphore actor](#e28)

- [E29 — Dependent QMD minimal experiment](#e29)

- [E30 — Binary transformation validation](#e30)

- [E31 — MPS and process interference](#e31)

- [E32 — Launch, graphs and CDP](#e32)

- [E33 — Power and steady-state behavior](#e33)

- [E34 — RAS contamination audit](#e34)

- [E35 — Platform and electrical evidence](#e35)

- [E36 — toolchain and library compatibility](#e36)

- [E37 — New PTX spelling on old silicon](#e37)

- [E38 — Negative-space falsification](#e38)

- [E39 — Complete composition usefulness](#e39)


---

<a id="a00"></a>


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


---

<a id="a01"></a>


# A01 — Index by computational need

> Enter through the problem, not through a presumed CUDA implementation.

**Status:** source-backed synthesis. **Depth:** 0.
**Read when:** search, routing, index.
**Prerequisites:** none. **Evidence:** original synthesis; see linked mechanisms.

## Query routes

| Need | Mechanisms | Compositions | Required depth | Tests | Decision cue |
|---|---|---|---|---|---|
|Sparse support / intersections|M01 M02 M06 M26|C00 C11 C37|R15|E11 E13|Start with packed logic; test tensor expansion only when reuse repays it.|
|Branchless sequence routing|M03 M04 M06 M07|C01 C02 C03|R06|E05 E13|Choose symbol encoding and lane ownership before control flow.|
|Small graph propagation|M14 M02 M29|C05 C24|R06|E14 E39|Register patches for local work; monotone merges only for the right algebra.|
|State machines / local dynamics|M01 M14 M30|C06 C10 C25|R15|E13 E16|Discrete circuits and continuous algebra are different representations.|
|Tiny dense algebra|M24 M25 M27|C10 C13 C16|R05|E09 E12|Inspect four native products and downstream fragment ownership.|
|Reduction / scan / threshold|M02 M26 M29|C12 C37|R15|E11 E12|Compare shuffle/POPC with tensor or carry-save constructions.|
|Lookup / category decoding|M03 M04 M23|C03 C31|R04|E05 E26|Register network, constant broadcast and texture have distinct regimes.|
|Packing / bounded integer math|M08 M09 M11|C07 C08 C09|R15|E01 E13|Prove carry, range and sign behavior before benchmarking.|
|Register pressure / operand ports|M12 M13 M14 M20|C17 C35|R02|E04 E30|Optimize the operand-read graph and state lifetime together.|
|Latency hiding / complementary pipes|M16 M15 M36|C18 C19|R14|E02 E03 E17|Overlap required work; do not add peak throughput figures.|
|Shared layout / transpose|M18 M25 M22|C16 C36|R05|E06 E09|Compose producer/consumer maps rather than canonicalizing every stage.|
|GPU-resident scheduling|M30 M15 M17 M33|C25 C34|R06|E16 E32|Compare a small resident palette to batching and graph replay.|
|Cross-GPU cooperation|M34 M35 M31|C20 C21 C22 C23|R07|E18 E19 E20|Compare pull, owner-compute, staging and information reduction.|
|Queues / publication / arbitration|M29 M31 M38|C04 C22 C24|R06|E14 E15 E22|Reservation, publication, reuse and progress are separate.|
|DMA / non-SM computation|M36 M37 M38 M39|C26 C27 C28|R09|E27 E28 E29|Separate observed HAL behavior from header-only and speculative interfaces.|
|Address-space tricks / memory tiers|M40 M41 M42 M43|C29 C30|R08|E08 E23 E24|Naming, backing, policy and coherence are distinct.|
|Approximation / mixed precision|M10 M28 M09|C14 C15 C31|R15|E10 E26|Budget actual arithmetic error; refine ambiguous decisions.|
|Metadata elimination|M02 M03 M14|C04 C35 C36|R01|E05 E13|Let stable position carry identity instead of loading indexes.|
|Dynamic adaptation|M46 M47 M42 M52|C32 C33|R12|E25 E33|The feedback signal must repay observation and switching.|
|Firmware / hidden engines / reset|M49 M50 M51|C39|R13|E34 E35 E38|Establish an accessible contract before treating silicon as capacity.|
|Compiler / binary manipulation|M48 M12 M13|C17 C34|R10|E30 E36 E37|Pin sm70 binaries and validate the complete executable.|
|Uncertain hardware behavior|M22 M34 M39|C38 C39|R00|E07 E18 E38|Look up the open question; do not silently invent a premise.|

## Conditional source reads

Read S03 for an exact ISA/target contract; S04 for historical empirical microarchitecture; S12/S15 for copy-engine fields versus observed commands; S27 for QMD fields; S20 for tensor numerical caveats; S16 for ATS/MMU implementation. These are different evidence classes.

Do not read every source just because a card lists it. Resolve the claim that could change the design. Mandatory correctness dependencies remain mandatory even when performance evidence can be deferred.


---

<a id="a02"></a>


# A02 — Performance field guide

> A compact reasoning guide to using Volta as a collection of computational mechanisms.

**Status:** source-backed synthesis. **Depth:** 1.
**Read when:** performance, creative synthesis, field guide.
**Prerequisites:** R00. **Evidence:** original synthesis; see linked mechanisms.


## 1. Change the representation before tuning its implementation

A logical actor can be a scalar record, a bit, a lane, a register slot, a tensor coordinate or a remote owner. These are not interchangeable in cost. Ask which semantic relationships become wiring when identity is positional. A32-vertex local support graph can turn an edge loop into AND/nonzero/ballot; the cost moves to loading and patch boundaries. C05/C35.

Bit slicing is not simply compression. It changes the arithmetic machine: word logic evaluates many one-bit instances. LOP3 becomes a Boolean circuit element; carry-save planes maintain per-position multiplicity without scalar counters. Keep the representation across several stages or its conversion cost will dominate. C00/C02/C06/C37.

## 2. Treat routing as computation

A warp is a constrained register-exchange network. A small lookup can be an owner-lane shuffle plus byte extraction. A butterfly can be lane ownership and XOR routing. A predicate mask can simultaneously describe membership, compact rank and a next destination. None of this requires an intermediate index array when producer and consumer agree on the mapping. C03/C04/C36.

The constraint is real: sources must participate, selected values must exist, multiword movement costs multiple operations, and dynamic local-array indexing may spill. “Register-resident” is something to establish in generated code, not a source-code annotation.

## 3. Use tensor units as bilinear circuits

The supported native sm70 decomposition permits four independent small products in one warp collective. This invites local state mixers, graph-patch correlations, structured transforms and counting encodings whose dimensions are not minibatch axes. But a reshape alone does not preserve an arbitrary operator. Write the equation and map its real dimensions. R05/C10.

The most promising gain may be keeping the result in native fragments through several operators. Avoiding canonical store/reload/transpose can exceed the value of the arithmetic itself. Precision and accumulator layout can change the routing cost. C16.

Tensor counting competes with extremely compact AND+POPC and DP4A. Tensor scan competes with a short shuffle tree. Hadamard/FFT-like transforms compete with structured add/shuffle circuits. Use these strong baselines. C11–C13.

## 4. Treat arithmetic domains as resources

Packed integer dots, guard-digit multiplication, FP64 bounded-integer work and SFU/table approximations can embody useful subproblems. The domain is chosen by the operation's invariants and the machine bottleneck. Every intermediate range, carry and error must be accounted for. C07–C09/C31.

A particularly useful composition is approximate screening plus exact refinement. A proved error interval allows exact final threshold decisions while a fast path rejects easy cases. The ambiguity mask is then a routing object. An empirical margin is not a certificate. C14/R15.

## 5. Optimize the operand stream, not only FLOPS

Register banks, reuse and dependency controls affect how values reach arithmetic. Think of hot instructions as a graph of operand reads. A tile with excellent HBM access can still feed arithmetic poorly; an extra amortized copy may improve a repeatedly conflicted operand path. Conversely, a local fix can cause spills. C17/R02.

Useful independent metadata work can hide arithmetic or memory latency. But separate pipes share issue, registers, memory and power. Compare isolated, serial and interleaved versions at equal useful work. More measured utilization is not proof of improvement. C18/R14.

## 6. Keep state alive when it buys more than it reserves

Persistent kernels can retain coefficients, small graphs and task state. A finite operator palette can avoid repeated launches and reloads. A giant universal interpreter may instead lose through code footprint, divergent dispatch and reserved resources. Compare proper batching and graph replay. C25/C34.

A resident consumer cannot occupy all slots needed by its producer. Independent-thread scheduling does not make arbitrary spin protocols fair. Every queue or phase requires participation, visibility and progress proofs. R06 is a required read, not optional caution.

## 7. Optimize information crossing the boundary

NVLink supports more than bulk copy, but direct remote loads are not always the right abstraction. Compare requester pull, bulk stage and a compact query answered by the owner. Keep the service overhead in the model. A support mask or delta may be a better wire representation than a dense tensor. C20/C21.

Local CPU pages and GPU owners can exploit separate host ingress paths when the actual topology supports them. Pinning does not establish locality, and avoiding an extra CPU copy does not eliminate PCIe DMA. R07/C23.

## 8. Include non-SM actors in the search

Pinned Volta UVM code demonstrates completion-word release, increment and timestamp commands with data transfer disabled. The copy engine is therefore not merely a memcpy implementation. Its class also exposes restricted component remapping and a broader semaphore-operation menu. These suggest format and control roles outside shader execution. M37/M38/C26/C27.

The boundary matters: semaphore reduction is not array reduction; declared remap fields are not a general public API; QMD dependent fields are not a proven arbitrary dataflow runtime. A careful low-level investigation can still be worthwhile when supported alternatives have a measured gap. C28/R09.

## 9. Use address space as a view, not as fictional coherence

VMM can change naming/backing relationships and potentially remove ring-window splits. ATS implementation details reveal that placement can also interact with translation policy on specific platforms. Neither observation merges execution domains or grants arbitrary page-table control. C29/C30/R08.

## 10. Let evidence determine how far to descend

A new PTX spelling can target old silicon: lop3.BoolOp is one such lead. A family opcode name can mislead about an exact GPU target. A driver header can reveal physical capability without exposing a safe application path. Keep the knowledge grade and reachability grade separate.

For every unconventional candidate, record the exact equation, representation, required contract, complete cost, strongest baseline and falsifier. Promote it only through semantic tests, legal compilation, binary inspection, isolated measurement and whole-workload benefit. A failed shape is a useful boundary, not a reason to erase the mechanism.


---

<a id="r00"></a>


# R00 — Reading and evidence contract

> A design search space with explicit proof and reachability gates, not an assertion that every idea is fast.

**Status:** source-backed synthesis. **Depth:** 0.
**Read when:** evidence, reading, correctness.
**Prerequisites:** none. **Evidence:** original synthesis; see linked mechanisms.


## Two independent axes

Knowledge: **A** ISA/API guarantee; **D** NVIDIA implementation; **E** original empirical result; **R** reverse engineering; **H** reasoned hypothesis; **S** speculative lead; **U** unresolved. Reachability: **C** public CUDA/Driver API; **P** inline PTX; **B** cubin/SASS work; **K** driver/channel; **F** firmware/platform. A documented K feature is not a public C feature. An H composition may use only guaranteed primitives and still lose badly.

Local verification is a third field. This research did not execute on the user's V100 s. CPU tests in the package validate algebra and index mappings, not GPU instruction lowering, tensor rounding, memory coherence or speed. Historical numbers remain attributed to their experiment. Missing values are unknown, not zero.

## Select depth by the decision

Read the need index, then two or three M cards. Read a C recipe to see a concrete representation and falsifier. Read R06 whenever work shares mutable state across lanes/blocks/devices; R15 whenever precision is repurposed; R05 whenever exact MMA fragments matter. Source headers are worth loading only when a K-level capability or disputed implementation detail changes a design choice. Never inject the entire compendium into every kernel task.

Each mechanism is interrogated for physical action, scope/granularity, cost/concurrency, CUDA/PTX/SASS exposure, avoidable conventions, alternative role, compositions, attractive representations, correctness/fragility, provenance and an experimental discriminator. These fields are distributed across linked cards rather than repeated as twelve boilerplate headings.

## Promotion ladder

Algebraic equivalence → legal operand form → participation/visibility/progress proof → generated binary inspection → isolated measurement → interference measurement → complete-workload benefit. Passing one stage does not pass the next. A speedup claim needs its shape, distribution, preprocessing reuse, accuracy and topology.

A negative result should identify the failed representation and regime. “Tensor cores are bad for graphs” is not a useful record; “this packing at this density loses after conversion” is. Preserve superseded claims and failed tests so another agent can revisit the actual premise.

## Remaining frontier

The atlas does not contain a complete SXM2 schematic, all NVLink packet/credit details, exact remote-cache policies, every queue limit or a firmware programming contract. Those questions remain indexed, not silently answered by analogy. The original 0–140 scope is retained. No meta-device implementation is chosen.


---

<a id="r01"></a>


# R01 — Machine reference

> Separate the enabled product from the full die, and independent engines from shared bottlenecks.

**Status:** source-backed synthesis. **Depth:** 1.
**Read when:** overview, resources, topology.
**Prerequisites:** none. **Evidence:** S01 S02.


| Resource | Reference point | Design implication |
|---|---|---|
| SM execution |4 scheduler sets;64 FP32,32 FP64,64 INT32,8 tensor units | Partition-local issue and operand supply matter. |
| Residency |64 warps;64 K32-bit registers;255 regs/thread;32 CTAs/SM | Register circuits trade locality against admitted work. |
| Local storage |128 KB combined L1/shared/texture; shared through 96 KB | Carveout changes two resources together; large shared requires opt-in. |
| Memory |4 HBM2 stacks; nominal 900 GB/s | More clients do not create more owner-memory bandwidth. |
| Fabric |6 NVLink2 ports,25 GB/s per direction each | Count installed links per pair; do not use aggregate bidirectional numbers as one-way rates. |
| Module |OriginalS X M2 nominal 300 W,140×78 mm | Sustained clocks depend on cooling and shared power. |

Facts: S01/S02. The user's SKU, capacity, active SMs, link wiring and host roots were not inventoried. Full GV100 resources and shipping V100 resources are not identical. Query rather than assuming16 GB,32 GB or80 SM.

The most useful abstract machine is a hierarchy of state owners. A lane owns registers. A warp exchanges selected values. A block owns shared state and barriers. An SM contains several issue domains. A GPU's clients contend for caches, memory controllers and front-end submission. A peer GPU contributes remote memory service, not local shared memory. Copy engines and command completion are additional actors with different interfaces.

Before choosing an algorithm, decide whether identity should live in a bit position, lane, register slot, shared bank, numeric fragment or physical owner. Positional identity can remove metadata only when producer and consumer share a reversible stable mapping. Physical SM numbering is not such a portable semantic map.

A scalar instruction, coalesced request, cache sector, HBM burst and link packet are different granular i ties. One source operation can create many transactions; one bitwise instruction can evaluate many independent logical decisions. Optimizing the wrong granularity is a common failure of nominally low-level code.


---

<a id="r02"></a>


# R02 — Execution, scoreboards and operands

> Model the dependency graph and operand-delivery graph together.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** scheduling, registers, scoreboards, occupancy.
**Prerequisites:** none. **Evidence:** S01 S04 S05 S30.


For an operation latency L and issue opportunity I, enough independent chains are needed to cover roughly L/I opportunities. This is a lower bound, not a scheduler simulator. Resource ceilings alone do not tell how many warps are eligible. Static warp-to-scheduler ownership means an apparently well-occupied SM can still have unbalanced issue domains. Distinguish dependence, operand, structural, memory, barrier and instruction-fetch stalls.

Registers are storage plus ports. S04's parity-bank measurements motivate a source-read hypergraph: an instruction connects the distinct operands it must read, while reuse can remove some reads. Renaming to fix one hot instruction can lengthen live ranges or hurt another. A nominal extra move can be profitable when it prevents repeated port conflicts; it must be measured against added issue and capacity cost.

Dynamically indexed C++ local arrays are not a guarantee of indexed register storage. A warp-local table needs an explicit owner-lane and small local-register selection scheme. Keep hot state statically expressible; move cold fields elsewhere when the trade is favorable.

Historical dependence priors from S04, in cycles: common FP32/logic 4; IMAD 5; packed half 6; FP64 arithmetic 8; POPC 10; FLO/BREV/MUFU 14. These are not current compiler guarantees or reciprocal-throughput numbers. Record clocks before converting to time. Exact forms and operand patterns matter.

SASS dependency barriers, stall/yield and reuse controls are part of the executable schedule. Removing a wait may fail only under a longer memory latency. A binary transformation requires complete use/def/control metadata and differential tests, not just plausible opcode order.

Persistent execution can preserve useful register state across tasks, but it also holds residency. A consumer cannot assume a producer will eventually be scheduled if consumers occupy every slot. SM identity is an observation, not ordinary-CUDA placement authority. These are scheduling constraints to design around, not reasons to discard persistent computation.


---

<a id="r03"></a>


# R03 — Memory as algorithmic structure

> Track useful information per transaction, translation footprint and reuse lifetime.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** memory, HBM, L1, L2, TLB, shared.
**Prerequisites:** none. **Evidence:** S01 S04 S16 S30 S31.


For each access family record useful bytes U, transferred bytes X, request count Q, physical owner, reuse interval, alignment and translation working set. U/X can explain a graph traversal better than achieved G B/s. A metadata-heavy workload may be limited by issue or translations while HBM utilization looks low.

Partition data by role: hot support/routing metadata; evolving local state; streaming payload; cold exceptional state. These roles can justify different representations and paths. A producer that emits the consumer's native layout can remove an entire gather/transpose, not merely make it faster.

Shared memory gives explicit placement and phase synchronization; caches provide policy/replacement behavior. A same-word broadcast and different words in the same bank are not equivalent. Bank conflicts are not a contractual arbitration mechanism. XOR swizzles or padding must be evaluated through the next consumer too.

Shared carveout, cache capacity and spills interact. A few deliberate cold spills can buy enough independent work to win; uncontrolled hot accumulator spills usually have a different cost. Compare total local-memory traffic, live state and end-to-end time. L2 can hold compact coordination data, but arbitrary line residency is not guaranteed and later persistence controls are not a Volta assumption.

Cache operators do not establish happens-before. Read-only/texture paths are not automatically coherent aliases for writable data. The exact requester/owner cache behavior of peer traffic remains a path-specific experiment. This atlas does not adopt a blanket claim that all remote loads are cached in the requester'sL2.

Translation is a second working set. Reordering by page can help even when data-cache hit rate barely moves. VMM allocation granularity is not automatically the actual TLB page size. Physical address hashes cannot be inferred universally from one virtual buffer.

To sustain bandwidth B with latency L and request payload s, roughly B·L/s outstanding payloads are needed before other limits. A single pointer chain therefore cannot exploit a wide link. Sometimes the winning transformation is to expose independent requests or send a compact query to an owner, rather than tuning the load instruction.


---

<a id="r04"></a>


# R04 — ISA families and generation traps

> Source intrinsic, virtual instruction and physical opcode are different contracts.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** PTX, SASS, integer, compatibility.
**Prerequisites:** none. **Evidence:** S03 S05 S08 S09 S30.


Candidate families: Boolean logic/predicates; shuffle/vote/match; byte permutation and funnel shifts; packed dots; carry/multiply-high/address arithmetic; scalar/packed floating arithmetic; conversion/SFU; shared/global/constant/texture paths; atomics/reductions; convergence/barriers; and documented half-input tensor forms. See S03/S05/S08/S09 for exact signatures.

Do not infer a one-instruction fast path from an intrinsic name. __fns, packed saturation, general conversion and division need sm70 disassembly. Conversely, clear Boolean source can already lower to optimal LOP3; inline PTX may only make the code less flexible without changing the binary.

A useful asymmetry: **lop3.BoolOp was added in PTX 8.2 but targets sm70**. A new spelling can expose old silicon. Its predicate is a Boolean combination of result-nonzero and an input predicate. This is not a proof that every operation in a new PTX manual works on Volta.

Do not import native cp.async, ldmatrix, mbarrier, TMA, warpgroup MMA, cluster/distributed shared, DPX, TF32/BF16/FP64 tensor modes, sparse MMA or lat erL2persistence into ordinary GV100 code. Software constructions with similar purposes have different costs/contracts.

The Volta SASS table's IMMA entry is not proof of GV100/sm70 integer tensor support. The broader family includes distinctions: documented integer WMMA targets sm72+, while other integer MMA forms have later requirements. Keep exact opcode form, GPU target and family branding separate. Any unsupported raw-form experiment remains a gated hypothesis, not a capability premise.

Predicated-off lane operations, issued warp instructions and real branch cost differ. Shuffle/vote are not fences. DP4A is not an integer tensor instruction. CUDA byte_perm does not expose every PTX prmt selector interpretation. A full-warp MMA operation is not four independently launch able8-thread instructions.

Workflow: define semantics → compile exact sm70 form → inspect SASS/resources → test edge values/participation → measure serial and independent forms → compose. Compiler flags, operand constraints and memory clobbers belong to the proof.


---

<a id="r05"></a>


# R05 — Tensor geometry and native register interfaces

> Treat supported MMA operations as fixed bilinear circuits, not as an obligation to batch conventional examples.

**Status:** source-backed synthesis. **Depth:** 3.
**Read when:** tensor, HMMA, fragments, small algebra.
**Prerequisites:** none. **Evidence:** S02 S03 S07 S22 S23.


Physical tensor-unit granularity, PTX warp operations and C++ WMMA tiles are different levels. The sm70 half-input m8n8k4 form computes four independent 8×8×4 products in one warp-collective instruction. That creates an opportunity for unrelated small transforms, but all required lanes still execute the same collective.

The logical lane groups are {0..3,16..19}, {4..7,20..23}, {8..11,24..27}, {12..15,28..31}. Do not branch so only one group executes.

For **row-major A, column-major B, FP32 C/D**, lane l holds four half values for each multiplicand, packed into two 32-bit operands. Logical positions are:

```
A: row=(l%4)+4*[l>=16], col=i, i=0..3
B: row=i, col=(l%4)+4*[l>=16], i=0..3
C/D: row=(l&1)+(i&2)+4*[l>=16]
     col=(i&4)+(l&2)+(i&1), i=0..7
```

This is the explicitly documented PTX form, not permission to reinterpret arbitrary WMMA fragment storage. CPU checks verify coordinate bijections; they do not validate GPU operand packing. FP16 accumulator layout differs and can change downstream conversion cost.

Design backward from the next consumer: which needed rows, columns, reductions or neighbors are already in one lane's registers? Which require a shuffle/shared exchange? Can an elementwise stage operate in the producer's ownership layout? Can composing two permutations cancel a canonical transpose? S07/S22/S23 supply useful implementation precedents.

The semantic axes can be actor×hidden-state, small transition coefficients, graph patches or basis components. They need not be minibatch×feature. But reshaping a vector does not preserve an arbitrary update operator automatically; write the actual equations.

One 8×8×4 product represents 256 MAC; four represent 1024 MAC/2048 nominal floating operations. This is an algebraic count, not issue latency. Track useful versus padded products, coefficient loading, conversions, fragment routing and extraction. A structured operator with many zeros may be cheaper as a shuffle/add circuit. R15 defines the numerical gate.


---

<a id="r06"></a>


# R06 — Participation, visibility and progress

> Every unconventional executor needs all three proofs; a faster flag is not a complete protocol.

**Status:** source-backed synthesis. **Depth:** 1.
**Read when:** synchronization, queues, atomics, correctness.
**Prerequisites:** none. **Evidence:** S03 S10 S17 S25 S30 S33.


**Participation:** all lanes named by a synchronized primitive must meet its contract. Capture logical membership before divergence. A selected shuffle source must participate and hold a defined value. A block barrier must have the intended arrivals; a warp mask cannot legalize a partial-warp MMA when the form requires the complete warp.

**Visibility:** atomicity, ordering, scope and cache visibility are different. Legacy atomic CAS/Add is not a general publication fence. A release flag protects preceding payload writes only when the reader's matching acquire and buffer lifetime are correct. Cache hints and volatile do not repair data races. Peer/GPU/CPU/external-DMA paths have different contracts; use the actual supported memory type and scope.

**Progress:** independent-thread scheduling is not arbitrary fairness. Streams may serialize. Busy consumers can occupy all resources needed by a producer. Cooperative grid synchronization needs supported admission/residency. A spin barrier in an oversubscribed ordinary grid can deadlock. MPS resource fractions do not prove a blocked producer can run.

The stream-memory API warns that dependencies expressed only through values are invisible to CUDA scheduling. The memory-level dependency graph and CUDA-visible event graph must be considered together. A correct value comparison can still sit in a deadlocked submission graph.

A queue protocol needs slot ownership, reservation, publication, reuse, sequence/epoch rules, wraparound bounds, cancellation, backpressure, stop/drain and peer-failure behavior. Reservation and publication are not the same event. An empty local queue is not distributed termination while messages or producers remain in flight.

Abstract SPSC publication pattern:

```
producer owns slot → writes payload → release-publishes epoch
consumer acquire-observes epoch → reads payload → release-publishes reuse
producer acquire-observes reuse before overwriting
```

This is a proof structure, not a promise that a particular atomic overload works on every peer/mapped-host allocation. Tests can find failures but cannot legalize an operation outside the documented memory model. Use finite bounded tests and preserve a schedulable termination path.


---

<a id="r07"></a>


# R07 — NVLink, PCIe and NUMA as information boundaries

> Compare pull, push, staging and owner computation on the actual directed topology.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** NVLink, PCIe, NUMA, communication.
**Prerequisites:** none. **Evidence:** S02 S25 S26 S30 S33 S36.


Inventory each ordered pair: direct links, peer-load permission, native atomic support, performance rank, DMA route and host roots. Six ports on one GPU does not mean six links to a chosen peer. Distinguish one-way payload, simultaneous two-way payload, unloaded latency and saturation. n direct links gives a physical directional ceiling n·25 GB/s before overhead, not a measured guarantee.

Three data modes deserve comparison. **Pull:** requester loads selected remote fields. **Push/owner-compute:** owner filters/reduces a large local structure and sends a small result. **Bulk stage:** copy a region then reuse locally. Each can win in a different sparsity/reuse/latency regime. A remote service is a software construction, not a hardware remote launch caused by a pointer dereference.

Remote requests consume owner-side memory resources. Concurrent local compute can therefore change their performance even if requester utilization is low. Read-only remote caching must be measured for the exact instruction/allocation/path; do not derive coherence from a cache-speed plateau.

Do not assume aGV100 transparently routes arbitrary traffic through another GPU. NVSwitch is a separate component. POWER9 CPU coherence/ATS is a platform feature, not a generic property of two V100L2 caches on an x86 host.

Two GPUs attached to different CPU sockets can provide two ingress paths if data production and pinned-page placement align. Pinning does not itself guarantee locality. Avoiding an extra CPU copy does not eliminate PCIe DMA. Actual roots, switches, ACS/IOMMU and CPU-interconnect routing need inventory rather than inference from slot layout.

The deeper optimization is often information reduction. A frontier mask or query result may be a better transfer unit than the original tensor. Conversely, a thousand dependent remote scalar loads can cost more than one explicit staged tile. C20–C23 compare these possibilities without selecting any meta-device abstraction.


---

<a id="r08"></a>


# R08 — Virtual memory, ATS and faults

> Separate naming, backing, permission, residency and coherence before exploiting address-space structure.

**Status:** source-backed synthesis. **Depth:** 3.
**Read when:** VMM, UVA, ATS, TLB, managed memory.
**Prerequisites:** none. **Evidence:** S16 S18 S28 S29 S31 S38.


For any pointer ask five questions: who can name it, what physically backs it, which access permissions exist, where its page resides, and which visibility/order rules apply. UVA, peer mapping, managed memory and explicit V MM answer different subsets. None creates one kernel scheduler across GPUs.

VMM can make physical regions look contiguous, but the pages can have different owners/costs. Aliases suggest wraparound views and immutable repeated data; concurrent use must satisfy the actual mapping/cache contract. Remapping is a synchronized phase change, not presumed cheap per-element dispatch. Query capabilities and allocation granularity rather than infer them from header availability.

A concrete low-level clue appears in S16: different apertures and a47-bit physical-address implementation; ATS and GMMU paths interact. A NO_ATS directory policy spans 512 MB virtual regions so CPU translations do not defeat intended GPU faults. This motivates allocation zoning on an appropriate platform. It does not give ordinary CUDA permission to rewrite PTEs, nor make x86 automatically support the POWER9 path.

Fault replay and access notifications are finite asynchronous control systems. S28 records a real overflow-clear ordering race; S29 shows batched notification/migration policy. They can inform coarse placement adaptation, but faults are not a sensible assumed replacement for fine-grained branches. Notification delay and migration cost can exceed the useful phase length.

Representation questions: can a graph be ordered by page locality; can a view remove modulo/descriptor work without data motion; can ownership match migration granularity; can immutable views share backing legally? Each needs both a semantic proof and a cost test. VMM granularity and TLB page sizes must not be conflated. Alias success in one microbenchmark is not a universal coherence contract.


---

<a id="r09"></a>


# R09 — The non-SM command machine

> Copy engines and launch descriptors expose restricted transformations and control, not merely transport.

**Status:** source-backed synthesis. **Depth:** 3.
**Read when:** DMA, QMD, driver, firmware, non-SM.
**Prerequisites:** none. **Evidence:** S12 S13 S15 S27 S37 S39 S40.


The copy class inS12 includes component remapping, constants, write suppression, pitch/block-linear addressing and conditional controls. This can be interpreted as a limited format transformer. A plausible experiment copies records directly into a consumer-friendly layout while SMs compute. It is not evidence of arbitrary gather/scatter or a public cudaMemcpy remap API.

S15 is stronger evidence for a second role: actual Volta UVM code emits semaphore release, increment and timestamp commands with payload transfer disabled. Thus a non-SM actor can perform completion-state work. Crucially, the reduction applies to the semaphore word, not every element of an array. A “DMA vector ALU” inference would be wrong.

The QMD definition inS27 contains circular-queue, dependent-descriptor, release-slot/reduction and resource/cache fields. Those expose a richer front end than a single opaque launch. They do not supply complete rules for reference counts, queue ownership, units, cancellation or self-modification. A scheduling-mask field is not automatically a mapping to CUDA `%smid`.

A disciplined escalation is public copies/events/graphs/stream memory operations; shader-based movement; exact cubin experiments; validated driver/channel construction; platform/firmware work. Performance can justify a deeper route, but layer depth is not itself an optimization. Compare public graph replay before building a QMD path.

Texture/surface facilities are immediately relevant where CUDA exposes them. Raster, media and embedded controllers need separateS KU/API/firmware evidence. Physical ancestry or an engine class in a source tree is not usable Tesla capacity. The productive question is: what operation already exists in this unit, and can useful semantics be encoded in its operands?


---

<a id="r10"></a>


# R10 — Toolchain and binary evidence

> Preserve a known sm70-producing toolchain and audit the executed path.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** compiler, SASS, CUDA, libraries.
**Prerequisites:** none. **Evidence:** S05 S06 S11 S14 S22 S23 S26 S34 S41.


S06 distinguishes hardware lifetime from compiler targets: CUDA 12.9 retains offline sm70 compilation; CUDA 13 drops targets below 7.5. R580 is the stated final older-architecture driver branch. This does not promise every current cuB LAS, P y Torch, Triton, NCCL or inference binary retains Volta kernels. Compiler, driver, library build and selected path must all agree.

For experiments prefer an explicit native sm70 cubin and record whether a PTX JIT fallback was used. Management tooling's displayed CUDA version need not be the installed compiler. Preserve ptxas version, flags, driver, library version, kernel resource usage and binary hash.

Disassemble the hot loop, not just a representative instruction. Check register count, spills, shared allocation, code size, predicates, conversions and actual memory operations. Clear high-level code may already produce the desired sequence; inline PTX can prevent useful compiler work. Conversely, one clever expression can expand into a slow selection network.

For B-level transformations preserve original and edited binaries plus a deterministic transform. Resource metadata, relocations, constants, global state, branch/call targets and dependency controls are part of correctness. Random output tests are necessary but insufficient for memory-order or variable-latency scheduling assumptions.

The atlas uses pinned CUTLASSv2.11.0, NCCLv2.18.6-1 an dR580.95.05 source as evidence, not a deployment mandate. Moving open-gpu-doc headers are date-stamped but not commit-pinned; capture exact commit/hash before constructing commands. Current profiler/MPS documentation can describe features unavailable on the installed Volta stack. Compatibility is an explicit experiment, not a broad family-name assumption.


---

<a id="r11"></a>


# R11 — Performance model for circuit bending

> Compare complete semantic work, including conversions and synchronization.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** cost model, representation, break-even, optimization.
**Prerequisites:** none. **Evidence:** original synthesis; see linked mechanisms.


For representation R:

```
T(R)=Tencode+Tcritical_schedule+Tsynchronization+Tdecode
Tcritical_schedule >= max(dependency path, each shared-resource demand/service rate)
```

This is a lower bound, not a simulator. Different execution pipes can share issue slots, register ports, cache/memory and power. Sum of peak rates is not a realizable machine model. An interleaved kernel only helps if it performs work the application actually needs.

A representation wins after reuse n when n·per_use_saving > encode+decode+maintenance. A bitset maintained every step has different economics from immutable support. A fragment retained across ten operators has different economics from one expanded binary matrix product.

Latency hiding needs enough independent chains and request concurrency. More occupancy can increase independence but reduce locality or force smaller tiles. A large register circuit can be efficient with fewer warps when it has internal ILP; it can fail badly if it is one long dependency chain. Measure eligible work, not merely resident threads.

For communication, compare startup+payload/B+local work for direct pull, bulk stage and owner-compute. Queue/publication/response belongs in startup, not an omitted detail. Owner-compute is attractive when it reduces information crossing the boundary enough to repay service overhead.

For sparse versus dense, track useful tile work U/issued work W. Sparse paths pay metadata/gathers/control; dense paths pay zeros/padding/conversion. Density alone is not a decision rule. The operator's reuse and native representation determine the crossover.

Dynamic adaptation needs a remaining-horizon estimate and hysteresis. Switch only if expected future saving repays observation, repacking, cold state and uncertainty. A sophisticated profiler-backed policy can lose to a cheap density heuristic.

A reusable performance claim names semantic operation, in put distribution, output contract, baseline, preprocessing reuse, numerical error, bytes, instruction mix, clocks, repetitions, median/tails and raw results. An isolated “2×” is not architecture knowledge. Record failures just as precisely.


---

<a id="r12"></a>


# R12 — Measurement discipline and obs er v ability

> Use measurements to discriminate explanations, not merely collect impressive counters.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** microbenchmarks, profiling, counters, validation.
**Prerequisites:** none. **Evidence:** S04 S34 S35 S36.


Separate host latency, stream-event intervals, device instruction timing, disassembly, resource counters and telemetry. They are different observers and clocks. Cross-device clock alignment is an experiment; do not subtract peer global timer values as if synchronized.

For dependence latency create a true chain and consume its result. For throughput use independent accumulators and account for loop/measurement overhead. For memory separate pointer chase from streams, warm from cold, local from peer, read from write. For atomics vary address contention and returned-value dependence independently.

A single latency plateau does not prove a cache level. Sweep working set, stride, concurrency, page policy and cache form. A measured address conflict is useful even when the physical hash remains unknown, but allocation dependence must remain explicit. Do not identify HBM bits solely from one CUDA VA range.

CUPTI tracing, callbacks, counters and sampling have different availability/overhead. Nsight Compute can replay kernels and alter cache/clock conditions. A replayed isolated kernel is not the same experiment as a live persistent multi-GPU pipeline. Keep uninstrumented end-to-end timing and diagnostic collection separate.

Runtime feedback may need only queue depth or epoch duration. A coarse controller can select among prevalidated representations while preserving a fixed-policy baseline. Include measurement cost, lag and noise in the policy objective.

Capture UUID/SKU, VBIOS, driver, compiler, flags, libraries, cubin hash, clocks, power, temperature, ECC, link state, NUMA, IOMMU, page policy, launch resources, profiler/replay and raw outputs. The forty E cards are test protocols, not forty implemented benchmarks. CPU algebra tests and a read-only capability probe are supplied separately; no GPU measurements are claimed.


---

<a id="r13"></a>


# R13 — Electrical, firmware and reliability frontier

> Keep the less-public platform questions visible without inventing a schematic.

**Status:** source-backed synthesis. **Depth:** 3.
**Read when:** SXM2, electrical, firmware, RAS, reset.
**Prerequisites:** none. **Evidence:** S02 S28 S36 S37 S38 S39 S40.


The whitepaper documents module-level identity, nominal power, memory and interconnect organization. Management APIs expose some runtime identity, telemetry and reset controls. Original driver sources reveal pieces of graphics/context initialization, authenticated bootstrap, MMU, FIFO and fault handling. This is meaningful evidence below CUDA, but not a transistor-level machine description.

Missing are a validated complete SXM2 pin map, VRM schematic, strap matrix, PLL graph, al lO EM differences and full NVLink framing/credits. Exact module/baseboard part numbers and firmware matter. Connector form factor does not prove identical routing or enabled features.

Software-visible consequences include negotiated links/PCIe widths, sustained clocks, power competition and group recovery. A reset may affect connected peers. ECC events, retired pages, link retries and thermal throttling can contaminate a benchmark. Do not infer a speed benefit from disabling ECC; HBM sideband ECC differs from older arrangements.

Embedded controllers have real jobs and privilege boundaries. Their existence is not evidence that arbitrary user code can use them as spare cores. An exposed control/telemetry interface can still be a useful slow supervisory plane. Study boot/reset to locate the boundary between silicon, firmware and driver policy before proposing modifications.

Graphics/raster/media appropriation remains SKU/interface-gated. Texture interpolation through a documented CUDA path is a much firmer candidate than assuming an inaccessible codec or shader stage exists on this Tesla product.

The frontier ledger includes exact remote-cache behavior, HBM/L2 hashing, queue depths, raw instruction forms, firmware ABI and engine-reset granularity. A targeted source or experiment may resolve one. Repetition of a plausible story does not.


---

<a id="r14"></a>


# R14 — Composition, conflict and scope map

> Independent mechanisms often meet again at a shared bottleneck.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** composition, concurrency, scope, granularity.
**Prerequisites:** none. **Evidence:** S01 S12 S15 S25 S26 S30.


| Pair | Potential overlap | Shared limit to test |
|---|---|---|
|INT metadata +FP32|execution paths|issue, registers, dependencies|
|Tensor +prefetch|arithmetic vs outstanding loads|live registers, LDST, HBM, barriers|
|Tensor +conversion|independent instructions|conversion throughput, fragment routing|
|DMA +SM compute|different actors|HBM, fabric, power|
|Peer reads +local arithmetic|remote service|request slots, owner HBM, requester issue|
|Two transfer directions|possible engines/paths|engine assignment, roots, HBM|
|Atomic queues +bulk data|control vs payload|hot addresses, L2partitions, fences|
|MPS clients|independent work admission|resources, contention, fatal fault domain|

This is an experiment matrix, not a table of simultaneous peaks. E03/E17 establish the actual interference.

Scope hierarchy: register→thread; shuffle/vote→participating warp; shared/barrier→CTA; global atomics→specified scope; peer operations→supported pair; host mapped→system path; command completion→stream/channel/engine contract; firmware→privileged platform. An abstraction name does not widen scope.

Granularity hierarchy: bit, byte/half, word, lane, warp, MMA tile, shared bank, transaction/sector, page, DMA command, link packet, epoch. The semantic unit need not be identical at every level. A support mask can describe many edges while a tensor tile processes only a dense neighborhood.

Boundaries: ordinary CUDA does not distribute one warp/CTA across separate V100s; peer addresses do not name remote shared memory; VMM does not aggregateS Ms; MPS does not combine GPUs; smid observation does not grant affinity. These constrain mechanisms, not the possibility of useful software composition.

A useful algorithm makes its control, payload and ownership boundaries explicit. Shared resource conflicts should influence scheduling and layout; undocumented location/hash assumptions must remain performance hints rather than correctness dependencies.


---

<a id="r15"></a>


# R15 — Numerical contracts for unconventional arithmetic

> An algebraic encoding needs range, rounding and extraction proofs before it becomes a kernel primitive.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** numerics, precision, tensor, counting, approximation.
**Prerequisites:** none. **Evidence:** S03 S20 S21 S24.


Input quantization, accumulation rounding, overflow/underflow, cancellation and output conversion are separate errors. FP32 accumulation cannot restore information already lost when inputs became FP16. S20 motivates targeted tests rather than modeling a tensor operation as any serial IEEE FMA chain.

For proposed binary counting, products are 0/1. Start with nonnegative exact inputs, zero/integer accumulators and a conservative bounded intermediate count, for example ≤2^23, then validate the actual form. This is a proposed sufficient-style test domain, not a newly established hardware theorem. Chunk long counts and combine in exact integer arithmetic when needed. Signed/exponent-packed encodings need bounds on every partial sum, not only the final answer.

For expansion A=Ah+Al, B=Bh+Bl, omitting AlBl from the four-term expansion leaves algebraic residual AlBl, bounded by ||Al||||Bl|| for a compatible norm. Three products still pay input, accumulator and combination errors. This is not a native full FP32 tensor mode.

A certified approximate filter can give exact final decisions: if |s−ŝ|≤ε, accept when ŝ−ε≥τ, reject when ŝ+ε<τ, otherwise refine. The bound includes the actual arithmetic model. Random agreement is not a certificate; ambiguity rate determines profitability.

Binary64 can represent bounded integers exactly, but every product/partial must remain representable. SFU seeds plus refinement or texture interpolation can approximate functions when the application owns an explicit error budget. NaN payloads, saturation, infinity×zero and denormal quirks must not silently carry control state without a proven contract.

The CPU suite checks identities, bit encodings and index maps. It intentionally does not emulate proprietary tensor rounding. E10 separates source-supported numerical observations from local future verification.


---

<a id="m01"></a>


# M01 — LOP3 as a bank of Boolean circuits

> Make each bit an independent logical instance, then synthesize its transition rule.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** Boolean, FSM, support, branch elimination.
**Prerequisites:** R04 R15. **Evidence:** S03 S05.

## Established substrate [A/D; reachability C/P/B]

LOP3 evaluates a three-input Boolean truth table independently across a word. The immediate selects one function shared by the bit positions. The newer BoolOp form can also produce a predicate from result-nonzero and an input predicate on sm70; compiler acceptance and actual lowering remain testable.

## Appropriation hypothesis

Represent cells, edges or finite-state instances as bits rather than scalar records. One gate then evaluates32 instances per lane. Fuse eligibility, exclusion and frontier masks directly. Full-adder sum and carry use LUTs0x96 and 0xE8; a mux uses0xCA under index4a+2 b+c. Shared subexpressions can make a whole state transition a small circuit.

## Cost and rejection boundary

Bits do not communicate without shifts/shuffles. A run-time-varying rule per bit cannot be supplied by one immediate LUT. Count live planes and conversion cost; explicit PTX may produce exactly the same code as clear Boolean source. Exhaustive8-case gate tests are cheap, but compound-network and boundary tests remain necessary.

## Next reads

Compositions: C00 C01 C06 C37. Experiments: E01 E37.


---

<a id="m02"></a>


# M02 — Mask rank/select as routing

> Membership, local index and next destination can live in the same word.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** support, rank, select, compaction.
**Prerequisites:** R04 R06. **Evidence:** S03 S08 S10.

## Established substrate [A; reachability C/P]

Ballot collects lane predicates. Population count below a lane gives its rank; bit searches select members. __fns has a specific base/offset/sentinel contract, not just the intuitive name “find nth bit.” Its sm70 cost must be inspected.

## Appropriation hypothesis

Use a support word as a compressed dispatch table. Rank assigns compact output positions; select picks a source; shuffle retrieves payload. Preserve masks between stages instead of expanding them to index arrays. Empty-set tests can suppress a larger operation, not merely one branch.

## Cost and rejection boundary

Word-width shifts and no-result sentinels need explicit handling. The selected source must be a participant. Sparse enumeration and dense fixed networks have different crossovers. POPC is not assumed to share ADD latency; a clever mask pipeline can still become a dependent popcount chain.

## Next reads

Compositions: C04 C05 C35 C37. Experiments: E01 E05.


---

<a id="m03"></a>


# M03 — PRMT as a tiny register lookup

> A byte-permutation unit can act as a limited table-selection circuit.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** PRMT, lookup, packing, sequence.
**Prerequisites:** R04. **Evidence:** S03 S08.

## Established substrate [A; reachability C/P]

Byte permutation selects from source-register bytes. CUDA byte_perm and the fuller PTX prmt selector modes are not identical, especially sign-replication behavior. The instruction works on a small fixed source set, not arbitrary memory.

## Appropriation hypothesis

Hold an eight-entry categorical table in two words and select four entries with a packed selector. Compose a shuffle for coarse owner-lane selection with byte extraction for a larger warp-resident table. Small transition tables, quantization/codebook decoding and sequence normalization are natural candidates.

## Cost and rejection boundary

Updating the table costs register work. Dynamic indexing of local arrays can spill, so explicitly structured selection matters. Compare shared and constant lookup, especially when indexes are uniform. Endianness, selector high bits and inactive owner lanes require tests; multiple words per owner add another selection stage.

## Next reads

Compositions: C03 C35. Experiments: E01 E05 E13.


---

<a id="m04"></a>


# M04 — Shuffle as a constrained routing fabric

> Choose lane ownership so exchanging a value implements useful computation.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** routing, registers, graphs, transpose.
**Prerequisites:** R02 R06. **Evidence:** S03 S10.

## Established substrate [A; reachability C/P]

Shuffle exchanges register values among specified valid warp participants. It does not make a warp a flat arbitrarily indexed register file, and it does not fence unrelated memory. Wider payloads require additional movement.

## Appropriation hypothesis

Build butterflies, local graph gathers, small sorting/routing networks or fragment transposes. A lane can own a vertex or coefficient bank so its number is an address. Keep the layout expected by the next exchange rather than restoring row-major order after every stage.

## Cost and rejection boundary

Source lanes must participate and own defined values. Arbitrary traffic can require many shuffles; compare shared-memory broadcast or reloading cheap coefficients. A low-count network may lengthen dependencies or register lifetimes. Count useful multiword movement and code size, not just shuffle mnemonics.

## Next reads

Compositions: C03 C05 C16 C36. Experiments: E05 E09.


---

<a id="m05"></a>


# M05 — Match as an ephemeral associative table

> Equality groups can share reservations, decoding and reductions without a stored hash table.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** match, grouping, atomics, metadata.
**Prerequisites:** R06. **Evidence:** S03 S10.

## Established substrate [A; reachability C/P]

Match-style primitives return masks of equal-valued participating lanes. Their supported scalar/key semantics are exact; they are not approximate similarity search or global deduplication.

## Appropriation hypothesis

Elect a leader per equal destination, make one atomic reservation for the group and distribute compact positions by rank. Equal keys can share parameter loads or decoding. Aggregate repeated destinations before they consume cache/atomic bandwidth.

## Cost and rejection boundary

All-distinct keys create overhead with no aggregation benefit. Group size and skew determine leader workload. Multiword keys need correct comparison; numeric equality and bitwise equality differ for some floating values. Reservation is not payload publication. Global equivalence requires another level beyond one warp.

## Next reads

Compositions: C04 C35. Experiments: E05 E14.


---

<a id="m06"></a>


# M06 — Ballot transpose and bit-sliced state

> Encode once and make several later stages operate directly on planes.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** bitplanes, sequence, FSM, compression.
**Prerequisites:** R04 R11. **Evidence:** S03 S08 S10.

## Established substrate [A + H composition; reachability C/P]

Balloting each bit of lane-major categorical values produces word-sized bitplanes. Reconstruction is separate work. The representation redistributes logical parallelism into bits; it does not by itself reduce the information content.

## Appropriation hypothesis

Keep support, sequence categories or small discrete states encoded across multiple transitions. Boolean equality, threshold and neighborhood circuits can avoid repeated scalar loads and branches. Bitplanes can also be the communication payload, especially when later stages need only selected properties.

## Cost and rejection boundary

Both transposes count. One comparison seldom amortizes them; many state steps may. Partial warps require valid masks and cross-word neighbors need explicit carries/boundaries. High-entropy floating states generally need a different representation. Do not re encode at every kernel boundary.

## Next reads

Compositions: C01 C02 C06 C21. Experiments: E01 E13.


---

<a id="m07"></a>


# M07 — Predicates and reconvergence as data representation

> Replace control only when masked work or routing is cheaper.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** predication, branch elimination, control.
**Prerequisites:** R02 R04 R06. **Evidence:** S03 S05 S10.

## Established substrate [A/D; reachability C/P/B]

Predicated lane behavior, warp instruction issue and branch/reconvergence cost are different. Volta independent-thread scheduling does not eliminate convergence or memory-order requirements. Predicate storage is finite and specialized.

## Appropriation hypothesis

Express short transitions as predicate-selected updates, or first group state into homogeneous cohorts before a longer operation. Fuse conditions into one mask. A small resident interpreter can use a fixed control circuit rather than a divergent switch for every object.

## Cost and rejection boundary

Executing expensive invalid alternatives merely to discard them is not a win. Predicated instructions can still consume issue opportunities. Do not rely on undocumented fault suppression. Long branch bodies may favor real branches. Measure active useful work, instruction count and divergence separately.

## Next reads

Compositions: C00 C06 C34. Experiments: E05 E30.


---

<a id="m08"></a>


# M08 — DP4A/DP2A as structural arithmetic

> Use packed integer dots without assuming integer tensor-core support on GV100.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** DP4A, integer, counting, quantization.
**Prerequisites:** R04 R15. **Evidence:** S03 S05 S08.

## Established substrate [A/D; reachability C/P]

Packed dot forms multiply byte/halfword components and accumulate under signedness-specific integer semantics. These are distinct from later documented integer tensor operations. Actual instruction selection needs the exact sm70 form.

## Appropriation hypothesis

Encode short category scores, correlations or bounded counts directly as packed inputs. Preserve integer exactness where floating expansion would be unnecessary. Several score channels can reuse one packed operand; coordinate the instruction stream with other useful work only after measuring shared issue costs.

## Cost and rejection boundary

A dot collapses products; it does not preserve four independent outputs. Prove accumulator range and sign extension. Packing dominates some one-shot uses. Pure binary intersections should be compared with AND+POPC, not an artificially slow scalar loop. Wider integer tensor forms must not be imported by family name.

## Next reads

Compositions: C08 C11. Experiments: E13 E03.


---

<a id="m09"></a>


# M09 — Packed SIMD and conversions as state operators

> Saturation, rounding and comparisons can embody transitions rather than bookkeeping.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** packing, conversion, quantization, state.
**Prerequisites:** R04 R15. **Evidence:** S08 S09 S03.

## Established substrate [A semantics; reachability C/P]

Packed arithmetic/comparison and conversion intrinsics expose defined semantics, not guaranteed single-opcode lowering. Numeric conversion differs from bit reinterpretation; ordinary packed addition can leak carries between intended fields.

## Appropriation hypothesis

Use bounded saturating states, packed comparisons or quantization directly into the format required by a late rD P4A/bitplane stage. Rounding can implement a discretization boundary; a conversion can remove a whole intermediate representation.

## Cost and rejection boundary

Inspect expansion and execution pipe. Validate signs, ties, out-of-range cases and guard bits. Per-field independence needs a proof or a saturating/SIMD form. Domain switching every instruction can cost more than remaining in one numerical format. Keep exact fallback for sensitive thresholds.

## Next reads

Compositions: C07 C08 C15. Experiments: E13 E03.


---

<a id="m10"></a>


# M10 — S F Us and interpolation as alternate arithmetic

> Use a different unit only with a deliberate error budget.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** SFU, approximation, nonlinear.
**Prerequisites:** R02 R15. **Evidence:** S01 S03 S04 S30.

## Established substrate [A/E; reachability C/P]

Special functions and texture interpolation have distinct precision, format and throughput contracts. A fast approximate primitive is not equivalent to a full library function. Historical latency is not a full concurrency model.

## Appropriation hypothesis

Build a nonlinear update from an approximate reciprocal/rsqrt seed and a correction. A table plus texture interpolation can embody a piecewise function. Choose the route that reduces the occupied bottleneck rather than merely the scalar operation count.

## Cost and rejection boundary

Singularities, large exponent ranges, subnormals and clipping boundaries need analysis. Include table setup, traffic and conversion. Compiler fast-math flags can change the contract rather than only the schedule. An unbounded approximation is not a safe exact decision filter.

## Next reads

Compositions: C31 C18. Experiments: E26 E03.


---

<a id="m11"></a>


# M11 — FP64 and wide integer paths as alternate resources

> A bounded subproblem can sometimes move to a different arithmetic domain.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** FP64, integer, pipeline.
**Prerequisites:** R02 R15. **Evidence:** S01 S03 S08.

## Established substrate [A/D + H composition; reachability C/P]

GV100 has substantial FP64 resources alongside integer carry/multiply-high/address operations. Binary64 exactly represents integers in its precision range; representable inputs alone do not prove products and sums stay exact.

## Appropriation hypothesis

Keep a bounded polynomial or accumulator in FP64 for several operations when integer/FP32 resources are the bottleneck. Conversely, wide multiply/shift constructions can implement bounded index transformations. Treat this as resource assignment over a proved subdomain.

## Cost and rejection boundary

Every intermediate must fit the exact range. Conversions,64-bit registers and shared issue can erase benefit. Negative rounding/division behavior needs equivalence tests. An advertised spare pipeline does not make extra operations free.

## Next reads

Compositions: C09 C18. Experiments: E13 E03.


---

<a id="m12"></a>


# M12 — Register banks as an operand-delivery circuit

> Storage placement can matter even when the arithmetic is unchanged.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** register banks, SASS, reuse.
**Prerequisites:** R02 R10. **Evidence:** S04 S05 S11.

## Established substrate [E/R; reachability C/B]

Original Volta measurements identify parity-selected banks and some three-source conflicts. Reuse changes the actual reads. This is empirical microarchitecture, not a PTX allocation contract.

## Appropriation hypothesis

Model each hot instruction as a source-read hyper edge. Arrange operands or introduce an amortized copy so recurring reads fit the bank supply. Choose a tile layout partly by how it feeds arithmetic, not only how it loads from memory.

## Cost and rejection boundary

Compiler register assignment may defeat source-level parity intentions. Binary renaming must update all uses and metadata. A fix can increase live ranges and reduce occupancy. Hold mathematical work and operating conditions constant before attributing a gain to banks.

## Next reads

Compositions: C17 C16. Experiments: E04 E30.


---

<a id="m13"></a>


# M13 — Operand reuse and dependency control

> The short-lived operand path is a resource distinct from register capacity.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** reuse, scoreboard, manual scheduling.
**Prerequisites:** R02 R10. **Evidence:** S04 S05 S11.

## Established substrate [E/R; reachability B]

Volta machine code carries dependency/stall/yield/reuse information invisible in ordinary CUDA. These fields influence when operands can be consumed and when a variable-latency result is safe.

## Appropriation hypothesis

Keep repeated operands close in the instruction stream and interleave independent work while a dependency matures. A small algebraic change can improve the operand stream even with the same FLOP count. Reuse-aware layouts can avoid rereading common coefficients.

## Cost and rejection boundary

These controls are correctness machinery. Removing waits because one run passed can fail at another memory latency. Preserve original cubins and exact transformations. Extra ILP that extends many live values can spill. Measure complete kernels after isolated schedules.

## Next reads

Compositions: C17 C18. Experiments: E04 E30.


---

<a id="m14"></a>


# M14 — Register-resident local state machines

> Avoid turning a small evolving state into memory after every operation.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** registers, FSM, graph, state.
**Prerequisites:** R02 R11. **Evidence:** S01 S03 S04.

## Established substrate [D/E + H composition; reachability C/P]

Registers are per-thread storage with finite allocation/residency cost. Shuffle supplies a separate exchange contract. Dynamically indexed local arrays are not guaranteed to remain registers.

## Appropriation hypothesis

Hold a small graph patch, sequence context or actor×hidden-state block for many updates. Compile the local rule as a register circuit and encode identity in lane/bit position. Spill or stage only cold state and phase boundaries.

## Cost and rejection boundary

This trades capacity for locality. If every step requires arbitrary global interaction, the representation may duplicate state and add transfers. Cancellation, checkpointing and ownership changes need defined boundaries. Measure live registers, eligible work and reuse length.

## Next reads

Compositions: C05 C06 C35. Experiments: E16 E39.


---

<a id="m15"></a>


# M15 — Warp and SM specialization

> Assign roles only when they can coexist and make progress.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** warp specialization, persistent, scheduling.
**Prerequisites:** R02 R06. **Evidence:** S01 S03 S30.

## Established substrate [A/D + H composition; reachability C/P]

Concurrent resident work is resource-limited and not a universal fairness promise. SM ID is an observation, not normal CUDA launch affinity. Cooperative launch changes admission requirements rather than erasing capacity constraints.

## Appropriation hypothesis

Give some work a loading, routing or queue-management role and other work a compute role. A persistent block can reuse local service state. Phase-specific roles may be better than permanently reserving idle warps.

## Cost and rejection boundary

A waiting consumer can starve its producer. All required block participants still reach barriers. Do not assume SM IDs are a compact semantic index. Skew can destroy a role split that worked on balanced traffic. Provide bounded stop/drain and capacity for producers.

## Next reads

Compositions: C19 C25 C34. Experiments: E16 E32.


---

<a id="m16"></a>


# M16 — Instruction-level parallelism and useful overlap

> Hide a dependency with required work, not with more busy work.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** ILP, latency hiding, occupancy.
**Prerequisites:** R02 R11 R14. **Evidence:** S01 S04.

## Established substrate [D/E; reachability C/P/B]

Different execution resources can overlap, but issue, operands and dependence chains still constrain them. Occupancy is not equivalent to eligible independent work. Outstanding requests are finite.

## Appropriation hypothesis

Interleave several local microcircuits, prepare future addresses and support masks, or prefetch the next tile while current arithmetic runs. A representation that exposes independence can outperform one with fewer but serial operations.

## Cost and rejection boundary

Compare equal semantic work in isolated, serial and interleaved schedules. Track register count and memory traffic. Do not sum advertised peaks. An apparently better utilization number can simply reflect extra work absent from the baseline.

## Next reads

Compositions: C18 C19. Experiments: E02 E03.


---

<a id="m17"></a>


# M17 — Instruction cache and phase factoring

> An enormous unrolled circuit can lose to a smaller stateful machine.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** instruction cache, unrolling, interpreter.
**Prerequisites:** R02 R10. **Evidence:** S04 S05.

## Established substrate [E; reachability C/B]

Original measurements identify multiple Volta instruction-cache levels. Code size, branch targets and repeated sequences can matter independently of data-cache behavior.

## Appropriation hypothesis

Factor repeated operations into compact phases; specialize the hot case and route rare complex transitions elsewhere. A small register-state interpreter can be a candidate when a fully unrolled palette stresses fetch and live state.

## Cost and rejection boundary

Dispatch, calls and lost cross-phase optimization can outweigh locality gains. Sweep footprint with equal work. A historical capacity is not a universal sharp threshold. Inspect instruction stalls and spills before blaming the code cache.

## Next reads

Compositions: C34. Experiments: E02 E30 E39.


---

<a id="m18"></a>


# M18 — Shared memory as a banked routing network

> Layout can make broadcast and exchange the main computation.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** shared, banks, transpose, routing.
**Prerequisites:** R03 R06. **Evidence:** S01 S30 S04.

## Established substrate [A/D/E; reachability C/P]

Shared storage is block-scoped and banked with documented broadcast cases. Its capacity is coupled to the shared/L1 configuration. Conflicts serialize accesses without promising a useful arbitration order.

## Appropriation hypothesis

Assign local ownership to lanes/banks, swizzle repeated transposes and deliberately broadcast common coefficients. Store a scratch graph or transition table in a form chosen for its consumer. A shared layout can feed tensor fragments without a canonical intermediate.

## Cost and rejection boundary

Padding/swizzling costs addresses and can hurt the following stage. Distinct words in one bank are not a broadcast. Conflicts cannot substitute for atomics or barriers. Compare tiny exchanges to shuffles and count both producer and consumer phases.

## Next reads

Compositions: C16 C36. Experiments: E06 E09.


---

<a id="m19"></a>


# M19 — Barriers as phase boundaries

> A phase machine needs known participants and a schedulable producer.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** barriers, synchronization, phases.
**Prerequisites:** R06. **Evidence:** S03 S30.

## Established substrate [A; reachability C/P]

Warp, CTA and cooperative-grid barriers have different participant and ordering contracts. Named resources are finite. Ordinary oversubscribed grids cannot safely assume a global spin barrier.

## Appropriation hypothesis

Publish a tile, exchange state ownership or recycle a buffer at explicit phase boundaries. Independent work between phases can hide production delay. Count synchronization as part of the operator, not an invisible correctness tax.

## Cost and rejection boundary

Volta does not inherit later mbarrier or cluster-shared machinery. Divergence/early exits must preserve arrival contracts. A polling loop without a visibility/progress proof is not a cheaper barrier. Compare phase granularity and pipeline depth.

## Next reads

Compositions: C19 C25. Experiments: E06 E15 E16.


---

<a id="m20"></a>


# M20 — L1, local memory and deliberate cold spills

> The right question is useful residency, not zero spills at any cost.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** L1, spills, occupancy.
**Prerequisites:** R03. **Evidence:** S01 S04 S30.

## Established substrate [A/D/E; reachability C/P]

Local memory is memory-backed storage with caching, not extra registers. Register allocation and shared/L1 choices interact and can create residency cliffs.

## Appropriation hypothesis

Keep hot fields explicit in registers and allow rare state to live locally/shared. A few predictable cold loads may permit enough additional independent work to hide latency. Separate routing metadata from streaming payload to reduce pollution.

## Cost and rejection boundary

Uncontrolled spills in the hot loop can multiply traffic. Source array size does not reveal actual register use. Record local loads/stores, cache behavior and total time. Changing carveout can improve one path while harming another.

## Next reads

Compositions: C19 C35. Experiments: E07 E16.


---

<a id="m21"></a>


# M21 — L2 as a compact coordination service

> A large computation can have a very small shared control state.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** L2, atomics, coordination.
**Prerequisites:** R03 R06. **Evidence:** S02 S04 S30.

## Established substrate [D/E + H composition; reachability C/P]

L2 and global atomic handling participate in the device-wide memory hierarchy. Exact latency, address hashing and residency remain implementation/measurement questions. Later persistence controls are not assumed.

## Appropriation hypothesis

Keep queue heads, ownership words or support masks compact; aggregate locally before touching global state. Shard independent counters to reduce contention. Atomic OR/min/max can embody a merge algebra for suitable dataflow.

## Cost and rejection boundary

One hot address can serialize the algorithm despite large total bandwidth. False sharing, polling and fences matter. Do not rely on cache residency or infer peer coherence from local atomic success. Measure useful successful updates rather than raw attempts.

## Next reads

Compositions: C24 C25. Experiments: E07 E14 E18.


---

<a id="m22"></a>


# M22 — HBM and coalescing as layout constraints

> Bring useful fields together before optimizing the load instruction.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** HBM, coalescing, partitioning.
**Prerequisites:** R03 R11. **Evidence:** S02 S04 S30.

## Established substrate [D/E; reachability C/P]

Warp aggregation, sectors and memory-controller structure impose transaction granularity. One logical scalar request can move substantially more data. Not every address-to-bank mapping is publicly established.

## Appropriation hypothesis

Pack co-used state into the same transactions; separate cold metadata; order work to spread measured partition contention. Treat a discovered mapping as a tunable performance hint rather than immutable correctness state.

## Cost and rejection boundary

Optimize useful-byte fraction and reuse, not only G B/s. Allocation/page changes can alter inferred mappings. Copies, peer service and local work contend for owner HBM. A bidirectional link headline is not comparable to a one-way local-read rate.

## Next reads

Compositions: C23 C38. Experiments: E07 E08 E17 E20.


---

<a id="m23"></a>


# M23 — Constant and texture paths as function interfaces

> Specialized lookup behavior can embody a small operator.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** constant, texture, lookup, interpolation.
**Prerequisites:** R03 R15. **Evidence:** S03 S30.

## Established substrate [A; reachability C/P]

Constant broadcast benefits appropriate common addresses; divergent addresses change the cost. Texture sampling has explicit coordinates, formats and filtering behavior. Neither is a universal faster global load.

## Appropriation hypothesis

Store shared transition coefficients in a broadcast-friendly form. Use a tabulated smooth function plus interpolation as a nonlinear circuit element. Spatial lookup can sometimes suit the specialized cache/address machinery better than general pointer traversal.

## Cost and rejection boundary

Filtering precision, boundaries, conversion and update visibility are part of the contract. Random divergent constant lookups may serialize. Compare cached global, shared, manual interpolation andS FU routes at equal error tolerance.

## Next reads

Compositions: C31. Experiments: E26 E07.


---

<a id="m24"></a>


# M24 — Four native tensor microcircuits per warp

> The documented sm70 decomposition permits smaller semantic problems than conventional WMMA usage suggests.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** HMMA, tensor, small algebra.
**Prerequisites:** R05 R15. **Evidence:** S03 S22 S23.

## Established substrate [A/D; reachability P/C]

The supported half-input m8n8k4 form contains four independent 8×8×4 products but remains a collective warp instruction. Explicit lane ownership differs from arbitrary WMMA internals.

## Appropriation hypothesis

Map four graph patches, state-transition banks, basis changes or local reductions into one warp. Batch by reusable structure instead of only by examples. Keep fragments in a native representation for subsequent local work.

## Cost and rejection boundary

Pay for operand construction, zero padding, conversion and extraction. A vector reshaped into a tile does not preserve any desired operator for free. Do not execute only one 8-thread group or import later tensor formats. Validate mapping and numeric bounds first.

## Next reads

Compositions: C10 C11 C12 C13. Experiments: E09 E10 E12.


---

<a id="m25"></a>


# M25 — Fragment-native intermediates

> A result is already a usable distributed representation; canonical memory is optional.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** fragments, layout, registers, fusion.
**Prerequisites:** R05 R15. **Evidence:** S03 S07 S22 S23.

## Established substrate [A/E; reachability P/C/B]

Explicit PTX forms have defined lane/register ownership, while high-level WMMA fragment layout is not a portable raw-storage contract. Accumulator type can change conversion and shuffle costs.

## Appropriation hypothesis

Fuse masking, normalization, small transforms or another MMA in the existing producer ownership. Compose layout mappings so intermediate transposes cancel. An extra boundary permutation can remove repeated shared store/barrier/load phases.

## Cost and rejection boundary

Matching matrix dimensions does not imply direct fragment compatibility. Smaller move counts can lengthen dependencies or live ranges. FP16 storage may save registers yet lose on conversion or accuracy. Use ownership maps and complete pipeline timing.

## Next reads

Compositions: C16 C10. Experiments: E09 E10 E39.


---

<a id="m26"></a>


# M26 — Tensor counting and reduction

> Use ordinary algebra to encode structure, without imagining arbitrary semiring hardware.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** tensor, counting, reduction, support.
**Prerequisites:** R05 R15. **Evidence:** S03 S19 S20.

## Established substrate [A/E + H encodings; reachability P/C]

Binary0/1 products can represent conjunction and sums can represent counts. Prior work maps reductions/scans to tensor operations. This does not turn MMA into native Boolean, min-plus or arbitrary semiring execution.

## Appropriation hypothesis

Compute many shared-neighbor counts or category correlations with reused small dense blocks. Use a coarse score to route ambiguous cases to an exact bitset/integer stage. Repeated coefficient/state reuse can make structured numeric work attractive.

## Cost and rejection boundary

AND+POPC, DP4A and shuffle trees are strong baselines. Expanding bits to half, zero-work and output extraction can erase nominal throughput. Exactness requires a validated bounded numeric domain; CPU matrix identities do not establish tensor rounding.

## Next reads

Compositions: C11 C12 C14. Experiments: E10 E11 E12.


---

<a id="m27"></a>


# M27 — Tensor transforms and state mixers

> Fixed coefficient matrices can be configurable algebraic circuit elements.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** FFT, transforms, dynamics, tensor.
**Prerequisites:** R05 R15. **Evidence:** S03 S19 S21 S24.

## Established substrate [A/E + H composition; reachability P/C]

Small matrix products implement fixed linear transformations. Original work demonstrates tensor-based reductions, precision expansion and FFT-related transforms, with workload and format limits.

## Appropriation hypothesis

Encode local stencil mixtures, basis changes, Haar/Hadamard-like mixing or real/imaginary butterfly components. Reuse coefficients and fragment-native state across steps. The four native subproblems can carry unrelated transforms.

## Cost and rejection boundary

Structured zeros/ones may be cheaper as add/shuffle networks. A nonlinear transition needs lifting, piecewise selection or another primitive; putting it in a matrix does not make it linear. Bound range growth and include packing/coefficient load/extraction.

## Next reads

Compositions: C10 C13 C15. Experiments: E12 E39.


---

<a id="m28"></a>


# M28 — Mixed precision and certified decisions

> Approximate arithmetic is most useful when the final decision has an exact contract.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** precision, filter, refinement.
**Prerequisites:** R15. **Evidence:** S20 S21 S03.

## Established substrate [E + H composition; reachability C/P]

Input quantization, internal accumulation and output conversion are separate error sources. Targeted empirical evidence argues against assuming arbitrary scalar IEEE FMA equivalence for Volta tensors. Expansion requires additional operations.

## Appropriation hypothesis

Split values into high/low parts or compute a cheap score with an explicit error bound. Refine only ambiguous threshold cases using integer, bitset or higher precision work. Preserve a compact ambiguity mask for routing.

## Cost and rejection boundary

A guessed margin can silently remove true candidates. Cancellation/exponent gaps matter more than average error. Measure refinement fraction and conversion costs. Nearly universal refinement makes the filter strictly worse. No native full FP32 tensor mode is implied.

## Next reads

Compositions: C14 C15. Experiments: E10 E11 E39.


---

<a id="m29"></a>


# M29 — Atomics as merge algebra and state transitions

> Arbitration and convergence can be the computation itself.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** atomics, fixed point, ownership, state.
**Prerequisites:** R06 R15. **Evidence:** S03 S30.

## Established substrate [A; reachability C/P]

Atomics supply indivisible supported updates at a scope. Ordering of other data is separate. CAS exposes transition success; OR/min/max can supply useful merge functions. Contention serializes a target.

## Appropriation hypothesis

Use monotone idempotent merges for asynchronous dataflow when duplicates/order can be algebraically harmless. Use CAS for bounded ownership states and atomic reservation for compact outputs. Aggregate locally before crossing a global coordination boundary.

## Cost and rejection boundary

Overwrite and floating addition are not idempotent merges. Prove convergence, termination, fairness and wraparound. A flag does not publish surrounding data without the right ordering. Hot targets can dominate despite high aggregate bandwidth.

## Next reads

Compositions: C04 C24 C25. Experiments: E14 E15.


---

<a id="m30"></a>


# M30 — Persistent queues and resident interpreters

> Retain useful state and pay launch cost less often.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** persistent, scheduler, FSM, queues.
**Prerequisites:** R06 R02. **Evidence:** S01 S30 S25.

## Established substrate [A + H composition; reachability C/P]

A kernel can process bounded queued work while resident using normal supported memory/atomic primitives. This is not a special universal task-scheduling instruction.

## Appropriation hypothesis

Keep a finite operator palette, coefficients and support metadata hot. Process compact descriptors, group related tasks and steal work coarsely to balance skew. A task may be a small transform or local state update rather than a whole model layer.

## Cost and rejection boundary

Queue/dispatch/completion overhead must be amortized. Provide bounded capacity, stop/drain and producer progress. Large diverse palettes can inflate instruction footprint and lose optimization. Compare proper batching and graph replay, not an artificially launch-heavy baseline.

## Next reads

Compositions: C25 C34. Experiments: E14 E16 E32.


---

<a id="m31"></a>


# M31 — Stream memory waits and writes

> Commands can coordinate work without a polling shader, subject to the submission graph.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** streams, semaphores, synchronization.
**Prerequisites:** R06 R09. **Evidence:** S17 S30 S42.

## Established substrate [A conditional; reachability C Driver API]

Driver API wait/write operations have memory type, capability and comparison restrictions. Their hidden memory dependencies are not automatically visible to CUDA scheduling. Managed pointers are excluded by the documented contract.

## Appropriation hypothesis

Use a phase counter as a compact inter operation surface and compare command waits to tiny poll/update kernels. Batch control commands when legal. This is a way to use an existing command actor rather than reserve SM work.

## Cost and rejection boundary

A wait can block its own producer. Preserve CUDA-visible ordering where needed. Cyclic comparisons need bounded counter distance;64-bit and remote flush support are queried separately. A legal comparison alone is not a visibility/progress proof.

## Next reads

Compositions: C22 C27. Experiments: E22 E15.


---

<a id="m32"></a>


# M32 — Cooperative grids and historical multidevice launch

> Keep forgotten mechanisms in view, but retain their admission and version constraints.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** cooperative, grid, multi GPU.
**Prerequisites:** R06 R10. **Evidence:** S30 S03.

## Established substrate [A conditional; reachability C]

Cooperative grid synchronization depends on supported launch/capacity rules. Historical multi-device cooperative launch has additional requirements and lifecycle limits. Ordinary kernels do not inherit these guarantees.

## Appropriation hypothesis

Use a cooperative grid as a phase machine when global synchronization and resident resources fit. Study the old multi-device mechanism as a possible primitive and evidence of runtime design, not as fused hardware scheduling.

## Cost and rejection boundary

Check installed APIs and per-device flags. Deprecated is not necessarily absent, but not automatically durable. Oversized grids or unsupported interactions invalidate assumptions. No shared cache or cross GPU CTA follows from coordinated launch.

## Next reads

Compositions: C25 C39. Experiments: E16 E32 E36.


---

<a id="m33"></a>


# M33 — Graphs and device-side launches

> Pre built command structure and dynamic expansion solve different granularity problems.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** graphs, CDP, launch overhead.
**Prerequisites:** R09 R10. **Evidence:** S30 S32.

## Established substrate [A conditional; reachability C]

Graphs, streams and dynamic parallelism expose distinct submission contracts with version/device restrictions. A device child launch is not a general remote-GPU launch primitive.

## Appropriation hypothesis

Pre instantiate repeated phases and change only supported parameters. Compare coarse graphs to a resident interpreter for tiny tasks. Device-side expansion can be useful when discovery occurs on GPU and work is large enough to absorb launch cost.

## Cost and rejection boundary

Do not import modern device-graph or tail-launch features without target verification. Capture restrictions, lifetimes and implicit sync matter. Header availability does not show that a supported V100 execution path exists.

## Next reads

Compositions: C25 C28 C34. Experiments: E32 E36.


---

<a id="m34"></a>


# M34 — Peer loads as a distributed data path

> Direct access is one option alongside compact owner answers and staging.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** NVLink, remote memory, graphs.
**Prerequisites:** R07 R06. **Evidence:** S02 S25 S30.

## Established substrate [A/D conditional; reachability C/P]

Supported peer mappings let a GPU address another GPU allocation. NVLink can carry those transactions. Exact caching, packetization and routing behavior is not fully implied by pointer accessibility.

## Appropriation hypothesis

Keep immutable tables or cold metadata at an owner and pull selected fields. Coalesce requester lanes. For high work per byte, send a compact query to a resident owner service and return a reduced result. Choose by reuse and information volume.

## Cost and rejection boundary

Remote memory is not uniform latency local HBM. Many dependent loads may lose to a staged tile. Verify permissions, scope and atomic support separately. Do not make correctness depend on an unverified local/remote cache path.

## Next reads

Compositions: C20 C21 C23. Experiments: E18 E19 E20.


---

<a id="m35"></a>


# M35 — Remote atomics and NVLink signaling

> Use a narrow control channel only after checking the exact pair and operation.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** NVLink, remote atomics, queues.
**Prerequisites:** R06 R07. **Evidence:** S02 S25 S30 S32.

## Established substrate [A/D conditional; reachability C/P]

Native peer atomic capability is per ordered pair and does not follow from a successful copy. The allowed operation, scope and allocation determine the actual contract.

## Appropriation hypothesis

Publish epochs, mailboxes and completion counts for owner-compute services. Batch many payload changes under one publication to keep control traffic small. Assign ownership so every data access need not be remote.

## Cost and rejection boundary

Polling itself consumes requests and owner service resources. Visibility, reuse and progress still need proofs. Provide termination if a peer stops. Compare events and command waits, including idle power and tail latency.

## Next reads

Compositions: C20 C22 C24. Experiments: E19 E15 E22.


---

<a id="m36"></a>


# M36 — Copy engines as asynchronous workers

> Exploit independent progress without forgetting shared HBM and power.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** DMA, copy, overlap, latency hiding.
**Prerequisites:** R09 R14. **Evidence:** S02 S12 S15 S30.

## Established substrate [A/D; reachability C; deeper K]

Transfer engines execute commands separately from shader arithmetic. Engine counts, paths and concurrency depend on actual device/driver. They still share memory/fabric resources withS Ms and peers.

## Appropriation hypothesis

Prefetch future tiles, evacuate results or maintain buffered stages while compute proceeds. Compare raw DMA to SM movement that fuses filtering or format conversion. The useful path depends on transformation, not just byte count.

## Cost and rejection boundary

Asynchronous API return does not prove hardware overlap. Small copies are command-dominated; more buffers consume capacity. A DMA engine is not an arbitrary vector ALU. Measure concurrent traffic and critical path, not only isolated G B/s.

## Next reads

Compositions: C19 C23 C26. Experiments: E17 E03.


---

<a id="m37"></a>


# M37 — Copy-engine component remapping

> Investigate a restricted format transformer in the movement path.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** DMA, remap, packing, driver.
**Prerequisites:** R09. **Evidence:** S12 S15.

## Established substrate [D; reachability unverified; reachability K]

The Volta copy class exposes component selectors, constants, write suppression and structured addressing. Actual UVM code uses remapping for fills. A complete application route for arbitrary allowed selectors has not been established here.

## Appropriation hypothesis

Copy records with selected field order or constant padding directly into a consumer representation while SMs work. Treat the movement as a limited format stage. A careful descriptor can potentially remove a separate format kernel.

## Cost and rejection boundary

Not arbitrary AoS to SoA, and not a public cudaMemcpy promise. Component width/count, pitch, overlap and lifetime rules need proof. Deep interface setup can cost more than the saved work. Begin with isolated buffers and an owned validated command path.

## Next reads

Compositions: C26. Experiments: E27.


---

<a id="m38"></a>


# M38 — Semaphore arithmetic outside SM execution

> A completion word can be updated without a shader or payload transfer.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** DMA, semaphores, non-SM, coordination.
**Prerequisites:** R09 R06. **Evidence:** S12 S15.

## Established substrate [D; reachability K; public alternatives C]

Pinned Volta UVM code emits release, increment and timestamp commands with DATA_TRANSFER_TYPE_NONE. This is actual driver usage, not merely an enticing field. Reduction affects the completion word rather than an array.

## Appropriation hypothesis

Express phase completion or bounded event counting as command-engine work. A pipeline may publish progress without a tiny kernel or resident polling warp. A command timestamp can mark a different execution boundary from a shader clock.

## Cost and rejection boundary

Ordering, flushes, target permissions, counter wrap and queue ownership remain necessary. The private helper is not an ordinary callable CUDA API. Do not infer a free general ALU or shared time base across GPUs.

## Next reads

Compositions: C27 C28. Experiments: E28 E22.


---

<a id="m39"></a>


# M39 — QMD as a control object

> Dependent descriptors are a concrete research lead, not a complete hidden runtime.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** QMD, driver, dataflow, launch.
**Prerequisites:** R09 R06. **Evidence:** S13 S27 S40.

## Established substrate [D fields; S broader use; reachability K]

Official Volta QMD fields describe queues, dependent descriptors, releases, resource/cache controls and scheduling-related state. Initialization, ownership, reference counts and many operational rules require additional evidence.

## Appropriation hypothesis

Investigate whether fixed coarse phases can advance through dependency/release machinery with less CPU/SM mediation. Start with two known finite kernels and compare public graph replay. Treat the fields as a research map.

## Cost and rejection boundary

Address units, visibility, cancellation and firmware expectations can invalidate an apparently simple change. Do not patch live CUDA-owned QMDs blindly. A mask field does not automatically mean CUDA SM affinity. No arbitrary self-modifying task graph is claimed.

## Next reads

Compositions: C28. Experiments: E29 E32.


---

<a id="m40"></a>


# M40 — VMM views and virtual contiguity

> Change a view rather than moving bytes, when the exact mapping contract permits.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** VMM, alias, ring, layout.
**Prerequisites:** R08 R06. **Evidence:** S18 S31 S16.

## Established substrate [A/D conditional; reachability C Driver API]

VMM separates reservation, physical backing and permissions. Actual support and granularity must be queried. Naming one interval does not create uniform cost, coherence or one execution domain.

## Appropriation hypothesis

Investigate doubled virtual rings, shared immutable views and composite intervals. A legal alias can remove modulo/split window handling. A view can remove a descriptor layer without copying payload.

## Cost and rejection boundary

Confirm alias concurrency/cache contract and synchronize before backing changes. Mapping is per-phase, not assumed nanosecond dispatch. TLB pressure/granularity can outweigh saved address arithmetic. CPU alias intuition is not GPU evidence.

## Next reads

Compositions: C29 C30 C36. Experiments: E23 E08.


---

<a id="m41"></a>


# M41 — ATS and fault replay as coarse policy machinery

> Address translation can shape layout, but its useful controls are platform-specific.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** ATS, POWER9, MMU, faults.
**Prerequisites:** R08 R13. **Evidence:** S02 S16 S28 S38.

## Established substrate [D; reachability K/F; managed C]

Volta MMU source describes apertures and an ATS NO_ATS policy spanning 512 MB virtual regions. CPU translation can otherwise defeat an intended GPU fault. Replay uses finite hardware/software queues.

## Appropriation hypothesis

On an appropriate ATS platform, zone allocation classes by translation policy. Coarse fault/migration feedback can help placement. This is not an attempt to make every fine branch a page fault.

## Cost and rejection boundary

POWER9 features do not follow from x86 NVLink presence. Normal CUDA does not allow arbitrary PTE edits. Fault cost, lag and queue pressure can overwhelm benefits. Exact timing and user reachability remain unmeasured.

## Next reads

Compositions: C30. Experiments: E24 E35.


---

<a id="m42"></a>


# M42 — Access counters as delayed feedback

> Treat notifications as a policy signal, not an instantaneous free oracle.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** access counters, managed, adaptation.
**Prerequisites:** R08 R12. **Evidence:** S02 S29.

## Established substrate [D; reachability K; policy-dependent C]

Architecture and UVM source expose access-counter-based remote activity management, batching and thresholds. Shared source defaults are not a complete fixed V100configuration or application counter API.

## Appropriation hypothesis

Use demand epochs to decide migrate, replicate or remain remote. Add hysteresis and remaining reuse estimates. Optimize information boundaries rather than chasing individual misses.

## Cost and rejection boundary

Notifications maybe driver-owned and describe an obsolete phase. Migration competes for bandwidth and can oscillate. Establish an exposed low overhead signal before designing runtime feedback around it.

## Next reads

Compositions: C32 C30. Experiments: E24 E25.


---

<a id="m43"></a>


# M43 — NUMA-local host memory as a tier

> Align data production, page placement and GPU ingress.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** NUMA, PCIe, host memory, zero copy.
**Prerequisites:** R07 R08. **Evidence:** S30 S33 S36.

## Established substrate [A/D conditional; reachability C/OS]

Pinned/mapped host memory interacts with CPU placement, PCIe roots and IOMMU. Pinning does not necessarily make pages local. Mapped GPU access still traverses a transport with its own ordering contract.

## Appropriation hypothesis

Keep low bandwidth control or cold metadata in the appropriate host tier; stage hot payloads to HBM. Produced at a on the CPU side attached to the owning GPU to avoid unnecessary socket traffic.

## Cost and rejection boundary

Avoiding an extra CPU copy requires data already being local or produced there. It does not remove DMA. Verify actual roots and page placement; thread pinning alone is insufficient. Compare local, remote and simultaneous ingress.

## Next reads

Compositions: C23 C32. Experiments: E21 E35.


---

<a id="m44"></a>


# M44 — BAR, GPUDirect and external actors

> Reachable memory is not automatically an ordered shared protocol.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** BAR, GPUDirect, RDMA, PCIe.
**Prerequisites:** R07 R08 R06. **Evidence:** S33 S16 S30.

## Established substrate [A/D; reachability C/K/platform]

BAR mappings and peer registrations expose GPU memory under driver/platform rules. Aperture size is not necessarily total HBM or a permanent linear CPU view. External DMA has specific lifetime/ordering requirements.

## Appropriation hypothesis

An external actor can feed a GPU-owned pipeline or publish coarse work through a valid protocol. Studying registration/mapping also explains part of GPU peer addressing. Preserve explicit ownership at that boundary.

## Cost and rejection boundary

An external write visible in one domain need not be ordered before a running CUDA consumer. Root/IOMMU constraints and registration cost matter. A framebuffer mapping does not grant arbitrary MM IO/firmware control.

## Next reads

Compositions: C22 C23. Experiments: E21 E22 E35.


---

<a id="m45"></a>


# M45 — Contexts, IPC and MPS

> Multiplexing resources does not merge program semantics.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** contexts, MPS, IPC, isolation.
**Prerequisites:** R10 R06. **Evidence:** S01 S30 S41.

## Established substrate [A/D version-bound; reachability C]

Contexts own VA/module/execution state; IPC shares selected resources under explicit contracts. Volta MPS supports separate address spaces, not universal fatal fault isolation. Current MPS interfaces include newer variants not assumed on R580.

## Appropriation hypothesis

Use sharing/isolation deliberately for long lived services or independent work. IPC can separate control processes while preserving chosen data lifetimes. MPS is a precedent for multiplexing, not multi GPU aggregation.

## Cost and rejection boundary

Pointer identity, lifetime, fault scope and capture behavior change across processes. Resource percentages are not fairness/latency guarantees. Measure interference with the installed compatible version. Concurrent clients contaminate microbenchmarks.

## Next reads

Compositions: C25 C32. Experiments: E31 E36.


---

<a id="m46"></a>


# M46 — Counters as runtime feedback

> The observation must repay its own cost.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** counters, CUPTI, adaptation.
**Prerequisites:** R12 R10. **Evidence:** S34 S35 S36.

## Established substrate [A/D version-bound + H policy; reachability C/host]

Tracing, counters, sampling and telemetry differ incompatibility/overhead. Some collectors replay work, control clocks or caches, or require privileges. Current docs are not automatic V100support.

## Appropriation hypothesis

At coarse epochs choose between several validated layouts, tiles or push/pull policies. Cheap queue/time information may beat precise counters. Keep a fixed policy control and a bounded decision palette.

## Cost and rejection boundary

Replay measurement may not represent deployment. Noise can trigger oscillation; thermal drift can look like density change. Include instrumentation and switch cost and time-lag. Do not sample the entire machine just to answer a simple local decision.

## Next reads

Compositions: C32 C33. Experiments: E25 E33 E36.


---

<a id="m47"></a>


# M47 — Special registers and local clocks

> Observe placement and time without treating them as scheduling authority.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** smid, clock, global timer, persistent.
**Prerequisites:** R02 R12. **Evidence:** S03 S04.

## Established substrate [A/E; reachability C/P]

Special registers expose identity/timing with defined limits. smid need not be a dense portable task index; warp i dis not stable application identity. A global timer name is not a guarantee of synchronization between GPUs.

## Appropriation hypothesis

Label resident service instances, gather relative intervals or select local caches. Cross GPU timestamp exchange can estimate offset/drift only after accounting for message asymmetry. Use observations for performance policy, not correctness.

## Cost and rejection boundary

Compiler motion and missing dependencies can invalidate timing. Preemption affects identity assumptions. Do not depend on undocumented time slices or peer time alignment. Record measurement overhead and clock state.

## Next reads

Compositions: C25 C32. Experiments: E02 E16 E19.


---

<a id="m48"></a>


# M48 — Cubin and SASS transformation

> Machine-code experiments need complete executable evidence.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** SASS, cubin, compiler, rewriting.
**Prerequisites:** R10 R02 R06. **Evidence:** S04 S05 S11.

## Established substrate [D/R; reachability B]

Binary tools and original reverse engineering expose register assignment, opcodes and control metadata. PTX registers are not physical allocation. Code containers carry more than instruction bytes.

## Appropriation hypothesis

Test precise operand placement, schedules, dispatch or forms the compiler does not emit. A validated local transformation can become a reusable experiment primitive. Keep the compiler binary as control.

## Cost and rejection boundary

Branch/call targets, relocations, constants, globals, resources and dependencies must remain consistent. Passing one random test does not prove variable delay correctness. Pin versions/hashes and preserve the rollback path. No arbitrary kernel rewriter is claimed.

## Next reads

Compositions: C17 C34 C39. Experiments: E30 E37.


---

<a id="m49"></a>


# M49 — Embedded processors and firmware frontier

> Study exposed operations before imagining spare programmable cores.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** firmware, Falcon, boot, reset.
**Prerequisites:** R13. **Evidence:** S02 S37 S39 S40.

## Established substrate [D/R; S appropriation; reachability K/F]

Original driver sources reveal parts of authenticated boot, context and channel machinery. Embedded controllers have privileged duties and firmware boundaries; existence does not prove arbitrary user execution.

## Appropriation hypothesis

An exposed supervisory function could handle coarse health/power policy. Boot/reset study helps separate silicon from firmware/driver policy. Preserve unusual possibilities as leads with specific missing contracts.

## Cost and rejection boundary

No arbitrary firmware patching or signature bypass is assumed. Reset can involve peers. Controller RAM/ISA/ABI unknowns are open questions, not extra compute capacity. Require a minimal legal invocation before estimating performance.

## Next reads

Compositions: C33 C39. Experiments: E35 E34.


---

<a id="m50"></a>


# M50 — Graphics, media and dormant engines

> Shared die ancestry is not evidence of an exposed Tesla execution route.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** graphics, texture, media, raster.
**Prerequisites:** R09 R13. **Evidence:** S02 S30 S37 S13.

## Established substrate [D/R; S appropriation; reachability C where exposed; otherwise K/F]

GV100sources include graphics machinery and CUDA exposes texture/surface facilities. Specific Tesla API/firmware/S KU availability of other engines needs separate verification.

## Appropriation hypothesis

Candidates include interpolation as a function, format conversion in a data engine, or coverage-like operations on a legally exposed raster path. Only documented CUDA texture paths are treated as immediately reachable here; others remain gated leads.

## Cost and rejection boundary

An engine class does not prove usable Tesla throughput. Setup, data formats, precision and transfer cost can make appropriation useless even if legal. Do not import later GPU media features. First prove interface and outputs, then compare.

## Next reads

Compositions: C31 C39. Experiments: E26 E35 E38.


---

<a id="m51"></a>


# M51 — Faults, reset and RAS

> Long-lived computation needs a failure model as well as a fast path.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** faults, RAS, ECC, reset.
**Prerequisites:** R13 R08. **Evidence:** S02 S28 S36.

## Established substrate [D; reachability C telemetry; K recovery]

ECC, replay, retirement and link errors have different boundaries. The Volta fault buffer implementation contains an ordered overflow-clear workaround. Management reset can require linked older GPU groups.

## Appropriation hypothesis

Use health state to reject contaminated measurements and trigger coarse fallback outside hot loops. Checkpoint or use idempotent work boundaries so restart/replay has defined semantics.

## Cost and rejection boundary

Do not turn overflow into an intentional queue, disable protection for uncorroborated speed, or reset as routine benchmark setup. API recovery does not guarantee every engine is independently resettable. Validate outputs after faults.

## Next reads

Compositions: C24 C39. Experiments: E24 E34.


---

<a id="m52"></a>


# M52 — Power and thermal budgets as resources

> The best sustained schedule may differ from the maximum instantaneous overlap.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** power, thermal, clocks, adaptation.
**Prerequisites:** R13 R11. **Evidence:** S02 S36.

## Established substrate [D + H policy; reachability C management where permitted]

Compute, memory and interconnect activity share physical module constraints. Clocks/throttling depend onS KU, firmware, cooling and operating limits. Exact coupling is not fully specified here.

## Appropriation hypothesis

Interleave complementary phases or redistribute work away from a throttled critical path. Compare stable throughput and energy per result rather than brief cold peaks. A coarse controller can choose from validated schedules.

## Cost and rejection boundary

Staggering may increase energy or latency. Measure equal useful work at steady temperature and unchanged limits. No voltage/firmware modifications are proposed. Record telemetry averaging, environment and neighbor activity.

## Next reads

Compositions: C33. Experiments: E33 E25.


---

<a id="c00"></a>


# C00 — Bit-sliced full adders and arbitrary local Boolean rules

> Use the scalar logic data path as many parallel one-bit circuits.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** Boolean, FSM, support, LOP3.
**Prerequisites:** M01 M06 R15. **Evidence:** S03 S05.

## Construction [H; reachability C/P]


Let a, b, c be bitplanes. With truth-table index 4 a+2 b+c, LOP3 immediate0x96 computes parity and 0xE8 computes majority:

```
s = a ^ b ^ c
carry = (a & b) | (a & c) | (b & c)
```

At every bit position, a+b+c=s+2·carry. A mux a?b: c has immediate0xCA. Compose these gates into counters, threshold logic or a finite-state transition. A word carries32 independent instances;32 lanes can therefore hold1024 such instances per plane. Neighbor dependence becomes explicit shifts or shuffles rather than scalar pointer traversal.


## Why it could work

The identity is exhaustive over eight input triples. There is no floating rounding or cross-bit carry because carry is kept as a separate plane. Shared subexpressions can let a transition reuse masks across multiple output planes. A rule derived once can remain compiled while state evolves many times.

## Full cost and strongest baseline

Compare compiler-generated Boolean code, not only hand-written PTX. Include encoding, neighbor exchange, plane storage and extraction. A one-step scalar workload may never repay bit slicing. A variable rule per bit needs additional selection and cannot use one common immediate for free.

## Falsifier / rejection condition

Reject when encoding/decoding dominates, when the circuit grows beyond useful register/code footprint, or when required cross-instance dependencies turn each step into expensive routing. Exhaustively test small rules and valid-lane boundaries.

**Experiment:** E01 E13 E37. This composition has not been benchmarked on a V100 here.


---

<a id="c01"></a>


# C01 — Sequence symbols as two-plane equality circuits

> Change symbol comparison into a few word-wide gates.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** sequence, support, bitsets.
**Prerequisites:** M01 M02 M06. **Evidence:** S03 S08.

## Construction [H; reachability C/P]


Encode a four-symbol alphabet by two planes x0, x1. For another sequence y0, y1:

```
eq = ~((x0 ^ y0) | (x1 ^ y1)) & valid
matches = popcount(eq)
```

Position-shifted comparisons use shifts plus explicit cross-word carry or neighbor-lane exchange. A fifth ambiguous symbol needs another plane or a separate validity/wildcard rule; do not silently collapse it into one of the four. Compound motifs can reuse aligned planes and Boolean masks.


## Why it could work

Equality decomposes exactly into equality of encoded bits. The intermediate mask is directly useful for routing or support queries, so a scalar match array need never exist. Shifts turn positional relations into wiring.

## Full cost and strongest baseline

Compare byte-packed XOR/permutation and ordinary vector loads. Building bitplanes for one short comparison can lose. Include boundary symbols, reverse orientation and ambiguous-symbol semantics. Match counting and edit distance are different algorithms; this does not solve arbitrary alignment by renaming it.

## Falsifier / rejection condition

Reject when frequent orientation/window changes require more transposition than comparison, or when the consuming operator immediately needs expanded scalar symbols.

**Experiment:** E01 E13. This composition has not been benchmarked on a V100 here.


---

<a id="c02"></a>


# C02 — Ballot transpose as a persistent state encoding

> Use lane-to-bit transposition once, then keep the result as the working representation.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** bitplanes, packing, state, FSM.
**Prerequisites:** M06 M04. **Evidence:** S03 S10.

## Construction [H; reachability C/P]


For lane values x_l with k bits, form p_j=Σ_l(((x_l>>j)&1)·2^l), j=0..k−1. These planes are sufficient to reconstruct every valid x_l. Execute several Boolean/threshold stages directly on p_j. Store or transmit only the planes required by the next consumer.

Choose explicitly whether planes are replicated in lanes or distributed across owner lanes. Replication makes independent word circuits easy but consumes redundant registers. Distribution reduces duplication and requires exchange for gates involving multiple planes.


## Why it could work

The transform is an exact permutation of bits, not approximate compression. It makes one hardware word the natural unit of structural logic. A mask from one stage is already the next stage input.

## Full cost and strongest baseline

Compare maintained bitplanes to repeated encode/decode and to scalar packed states. Count all initial ballots and ownership shuffles. Lower bit cardinality and longer reuse improve the economics; arbitrary floating state does not magically become small.

## Falsifier / rejection condition

Reject when each stage changes the semantic grouping or needs individual scalar values so often that the representation cannot persist.

**Experiment:** E01 E05 E13. This composition has not been benchmarked on a V100 here.


---

<a id="c03"></a>


# C03 — A warp-resident byte lookup network

> Build a small exact table from register owners, shuffle and byte selection.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** lookup, PRMT, registers, routing.
**Prerequisites:** M03 M04 M14. **Evidence:** S03 S08 S10.

## Construction [H; reachability C/P]


A128-byte immutable table fits as one 32-bit word per lane. For index i∈[0,127], owner=i>>2 and byte offset=i&3. Shuffle the owner word to the requesting lane and extract the chosen byte. An eight-entry byte table can instead occupy two registers in each lane, with PRMT selecting several entries.

Larger tables require several words per owner and a second selection stage. Make that stage explicit: a dynamically indexed local array can spill rather than act like a register RAM. Choose replicated versus distributed tables by reuse and query correlation.


## Why it could work

Lane number becomes a coarse table address. The hardware exchange routes a whole packed word; extraction supplies the fine address. The scalar memory hierarchy is not used for each lookup once the table is loaded.

## Full cost and strongest baseline

Compare shared-memory tables, constant broadcast and cached global loads. Count table loading, register capacity and shuffle width. A uniform query can strongly favor constant memory. A partially participating warp needs a different ownership arrangement.

## Falsifier / rejection condition

Reject when updates are frequent, table size forces expensive register selection, or missing owners violate the collective contract. Test every index and byte ordering.

**Experiment:** E01 E05 E13. This composition has not been benchmarked on a V100 here.


---

<a id="c04"></a>


# C04 — Warp CAM plus one reservation per equal destination

> Combine match, rank and one atomic into compact grouped output.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** match, compaction, atomics, metadata.
**Prerequisites:** M05 M02 M29 R06. **Evidence:** S03 S10 S30.

## Construction [H; reachability C/P]


Group active lanes by equal destination key. Each group elects its lowest member as leader. The leader reserves popcount(group) output slots once. Broadcast the base to members; each lane writes at base+popcount(group & lower_lane_mask).

The reservation assigns disjoint indexes but does not publish completed payload. Add a separate release/acquire completion protocol when another actor consumes the slots before the kernel/stream boundary. Composite keys require exact equality rather than a los sy hash alone.


## Why it could work

Equal destinations share a local associative group without a persistent hash table. The rank formula is inject i ve within each group. Nonoverlapping atomic reservations make groups disjoint.

## Full cost and strongest baseline

Compare one atomic per lane and established warp aggregation. Sweep destination cardinality and skew. All-distinct groups can make matching overhead pure loss; one huge group can reduce atomics but create leader dependence.

## Falsifier / rejection condition

Reject if group discovery costs more than saved contention, or if the consumer requires an ordering that the proposed slot assignment does not preserve.

**Experiment:** E01 E05 E14 E15. This composition has not been benchmarked on a V100 here.


---

<a id="c05"></a>


# C05 — A32-vertex graph carried in warp registers

> Turn a small graph step into intersection tests and a ballot.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** graph, support, frontier, registers.
**Prerequisites:** M01 M02 M04 M14. **Evidence:** S03 S08 S10.

## Construction [H; reachability C/P]


Assign vertex l to lane l. Store its incoming-neighbor mask N_l as one word. Let F be a replicated frontier mask. Then next_l=((N_l & F)!=0), and a ballot of next_l gives the next frontier. Visited filtering is another mask operation.

This computes incoming propagation: using outgoing masks without changing the equation reverses the intended relation. For weighted or multi dimensional state, retain the support mask but introduce the actual numeric update separately. Graph patches can be connected by compact boundary messages.


## Why it could work

The adjacency row is a register and the frontier is a shared structural word. No per-edge pointer, explicit edge loop or intermediate Boolean array is required for a local unweighted step.

## Full cost and strongest baseline

Compare compact CSR and bitset baselines, including graph load and patch-boundary exchange. The fixed32-vertex geometry creates padding for small patches and partitioning cost for large ones. Useful reuse across many steps is the major opportunity.

## Falsifier / rejection condition

Reject when graph topology changes too frequently, when most edges cross patches, or when the actual update is not reducible to the proposed support operation.

**Experiment:** E01 E13 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c06"></a>


# C06 — A bit-sliced finite-state engine

> Compile small state transitions into gates rather than per-object branches.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** FSM, state, Boolean, branch elimination.
**Prerequisites:** M01 M06 M07 M14. **Evidence:** S03 S08.

## Construction [H; reachability C/P]


Encode a small state by q0..qk−1 planes. For a two-bit saturating counter with increment plane u:

```
s0=q0^u; carry=q0&u
s1=q1^carry; overflow=q1&carry
out0=s0|overflow; out1=s1|overflow
```

This maps0→1→2→3→3 wherever u is set and leaves other instances unchanged. More general finite transitions can be minimized into shared Boolean subexpressions. Keep event and validity planes alongside state.


## Why it could work

The rule is a finite truth function. Its circuit evaluates many instances with identical control and no divergent per-instance switch. State can stay in registers across repeated steps.

## Full cost and strongest baseline

Compare packed saturating intrinsics and conventional branch/predicate code. Circuit size grows with state/rule complexity; a huge truth table is not automatically cheap. Count event-plane generation and cross-instance information exchange.

## Falsifier / rejection condition

Reject when the state is genuinely high-dimensional continuous data, when rules vary independently per object, or when code/register growth exceeds the eliminated control work.

**Experiment:** E01 E13 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c07"></a>


# C07 — Guard-digit convolution using ordinary integer multiplication

> Use positional encoding to turn a bounded small convolution into multiply and extract.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** packing, integer, polynomial, convolution.
**Prerequisites:** M09 M11 R15. **Evidence:** S03 S08.

## Construction [H; reachability C/P]


Choose base B=2^g. Encode A=Σa_iB^i and D=Σd_jB^j. Their integer product has coefficient c_k=Σ_(i+j=k)a_i d_j at digit k **only if every coefficient is below B**, so no digit carry occurs, and the entire product fits the selected integer width.

For four digits in 0..3, maximum coefficient≤36. g=6 gives sufficient guard space; seven output digits occupy42 bits. Extract each coefficient with shifts and masks. Signed coefficients need a separately proved bias/correction scheme.


## Why it could work

This is exact schoolbook polynomial convolution embedded in integer positional arithmetic. Multiplication becomes a constrained small algebra engine. It is not carry less multiplication, arbitrary semiring arithmetic or an unlimited packing trick.

## Full cost and strongest baseline

Count encoding,64-bit multiply implementation and extraction. Compare DP4A, scalar multiply-add and a tensor construction where shapes align. Reuse of packed operands is crucial. Width and coefficient bounds must be checked for every chosen problem size.

## Falsifier / rejection condition

Reject on any possible cross-digit carry, overflow or unsupported signed correction. The CPU suite deliberately includes an insufficient-guard negative control to prevent over generalizing the identity.

**Experiment:** E01 E13. This composition has not been benchmarked on a V100 here.


---

<a id="c08"></a>


# C08 — Packed integer scores instead of float bookkeeping

> Keep a bounded short score in the integer representation that produced it.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** DP4A, scoring, counting, quantization.
**Prerequisites:** M08 M09 R15. **Evidence:** S03 S08.

## Construction [H; reachability C/P]


Pack four signed or unsigned byte coefficients and state values into matching DP4A operands. A short dot then produces one integer score. Reuse a packed input across several score channels; delay conversion until a consumer genuinely needs floating arithmetic.

Before choosing the domain, prove |accumulator|+Σ|products| stays inside the supported accumulator range. Define clipping/quantization and signs explicitly. For binary support counting, also implement AND+POPC as the stronger specialized baseline.


## Why it could work

The hardware already sums packed products. Avoiding expand-to-float and re convert can matter more than the arithmetic instruction itself. Short categorical scores and bounded integer filters are natural semantics.

## Full cost and strongest baseline

Compare packed loads, conversion and resulting instruction mix over the complete chain. DP4A loses independent product outputs. A quantizer maintained elsewhere has a different amortization than a quantizer run for every score.

## Falsifier / rejection condition

Reject if packing is one-shot overhead, if range proofs force frequent slow fallback, or if a simpler bitset circuit computes the same result with less information movement.

**Experiment:** E13 E03 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c09"></a>


# C09 — Exact bounded integers on the FP64 path

> Move a proved arithmetic subproblem rather than blindly seeking idle units.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** FP64, integer, pipeline, exactness.
**Prerequisites:** M11 M16 R15. **Evidence:** S01 S03.

## Construction [H; reachability C/P]


Identify an integer subproblem whose inputs, products and every partial sum remain exactly representable in binary64. Convert once, perform several operations in that domain, then convert back under a proved rounding/range contract. Candidate roles include bounded accumulations or index-polynomial evaluation.

The condition is stronger than “each input is below 2^53.” Intermediate multiplication and cancellation paths must also be safe. Division, remainder and bitwise operations generally need separate derivations.


## Why it could work

The same exact finite arithmetic can sometimes use a different execution resource. This is a capacity-allocation hypothesis, not an assertion that FP64 is always cheaper than integer work.

## Full cost and strongest baseline

Include conversions,64-bit register pressure, dependency length and shared issue. Compare native integer sequences with equal work. Benefit requires an actual bottleneck and an amortized domain change.

## Falsifier / rejection condition

Reject when any intermediate loses integer exactness, when conversions dominate, or when the supposed alternate pipe contends with the same limiting resource.

**Experiment:** E01 E03 E13. This composition has not been benchmarked on a V100 here.


---

<a id="c10"></a>


# C10 — Four tiny linear machines in one MMA warp

> Use the real native groups for local operators instead of pretending every row must be a batch example.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** HMMA, small matrices, state, graph.
**Prerequisites:** M24 M25 R05 R15. **Evidence:** S03 S22 S23.

## Construction [H; reachability C/P]


Assign one 8×8×4 product to each documented lane group. Fill A/B with actual semantic dimensions: local actors×latent components, transition coefficients, basis components or four unrelated graph patches. All32 required lanes execute the same instruction.

A dimension shorter than four can be padded. A longer contraction needs several instructions and a correct accumulation layout. Write the operator equation before assigning data; reshaping a vector into a square does not manufacture a useful dense relation.


## Why it could work

The product is bilinear and indifferent to whether its dimensions represent tokens, batches, genes or hidden-state factors. Independent native groups permit small structures without forcing unrelated values to mix.

## Full cost and strongest baseline

Compare scalar/register algebra and batched library paths. Track useful products versus padding, coefficient reuse, fragment loading and extraction. A fixed low-rank factorization can help only when it preserves the intended operator and saves enough work.

## Falsifier / rejection condition

Reject when the operation is mostly routing/addition, when inter-group exchange dominates, or when precision/range cannot support the semantic state.

**Experiment:** E09 E10 E12 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c11"></a>


# C11 — Tensor cores as common-neighbor counters

> Encode a batch of set intersections as binary matrix products, then test against bitsets.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** support, intersection, Jaccard, tensor.
**Prerequisites:** M26 M08 M02 R15. **Evidence:** S03 S19 S20.

## Construction [H; reachability C/P]


Let row X_i and row Y_j be binary incidence vectors over the same universe. C=XYᵀ gives intersection counts; union=|X_i|+|Y_j|−C_ij. Keep cardinalities separately and define the empty-union case for any similarity ratio.

Tile the contraction with supported half-input MMA and a validated bounded accumulation regime. For long universes, chunk and combine counts using exact integer arithmetic. Alternative output semantics include thresholded overlap rather than the full matrix.


## Why it could work

The algebra is exact over integers because binary multiplication is conjunction and addition counts. Tensor hardware can process many overlapping questions sharing the same decoded blocks. Whether its numerical path preserves the intended counts is a separate validation gate.

## Full cost and strongest baseline

AND+POPC on packed words is the primary baseline; DP4A is another. Tensor expansion moves many more bytes than packed support. High reuse and many pairwise queries may repay decoding; isolated intersections probably have a different optimum.

## Falsifier / rejection condition

Reject when expansion/padding/output traffic dominates, when count exactness fails, or when the application never needs the dense set of pairwise answers being computed.

**Experiment:** E10 E11 E13. This composition has not been benchmarked on a V100 here.


---

<a id="c12"></a>


# C12 — Prefix and reductions by structured matrices

> An all-ones or triangular matrix can encode data movement and accumulation.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** reduction, scan, tensor.
**Prerequisites:** M26 M27 R05 R15. **Evidence:** S19 S03.

## Construction [H; reachability C/P]


For a short vector x, an all-ones row yields a sum. A lower-triangular all-ones matrix L gives inclusive prefix es y=Lx. Several independent scans can occupy different native subproblems; longer scans require inter-tile carry propagation.

Keep the output in a useful fragment layout when possible. Padding and repeated coefficient loading must be counted; structured coefficients should not be materialized expensively for every tiny operation.


## Why it could work

These are exact algebraic identities. Prior original research establishes the general tensor reduction/scan direction; this recipe focuses on matching native Volta fragments and complete downstream use.

## Full cost and strongest baseline

A warp scan has a short shuffle/add network and is a serious baseline. Tensor approaches perform padded arithmetic and may need layout conversion. Floating summation order changes the numerical result even when the real-number equation matches.

## Falsifier / rejection condition

Reject for a lone short scan when a few shuffles win, or when extraction/inter-tile carries erase the fused benefit. Compare many simultaneous scans and fragment-resident producers separately.

**Experiment:** E12 E10. This composition has not been benchmarked on a V100 here.


---

<a id="c13"></a>


# C13 — Fixed transforms as configurable tensor circuits

> Use small basis changes, stencils or butterfly components as reusable coefficient banks.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** FFT, Hadamard, stencil, transform.
**Prerequisites:** M27 M25 R05 R15. **Evidence:** S24 S03 S23.

## Construction [H; reachability C/P]


Represent a local transform by a fixed small coefficient matrix. Hadamard-style ±1 mixing, small stencil neighborhoods, real-valued pieces of complex butterflies and local dynamical basis changes are candidates. Fit supported native shapes; compose phases while preserving native register ownership.

For a nonlinear operator, identify the true linear substep or a justified lifted representation. Do not claim that an arbitrary nonlinear function becomes a matrix merely by naming its state differently.


## Why it could work

The tensor primitive implements a reusable bilinear circuit. Fixed coefficients can be reused across many states or iterations. Original tensor FFT work demonstrates that non-neural transforms are a real direction, not just metaphor.

## Full cost and strongest baseline

Compare sparse add/subtract/shuffle networks. A Hadamard matrix has special structure a dense product does not exploit. Include coefficient preparation, normalization, range growth and complex-layout costs.

## Falsifier / rejection condition

Reject when the structured SIMT circuit has much less useful work, or when precision/error grows unacceptably across repeated transforms.

**Experiment:** E12 E10 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c14"></a>


# C14 — Certified approximate screening with exact refinement

> Use fast approximate algebra to avoid expensive exact work without changing the final decision.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** filter, precision, sparse support, refinement.
**Prerequisites:** M28 M02 R15. **Evidence:** S20 S21.

## Construction [H; reachability C/P]


Suppose a score s is compared with τ and a fast approximation ŝ has a proved error bound ε. Accept when ŝ−ε≥τ; reject when ŝ+ε<τ; otherwise refine exactly. Store ambiguous cases as a mask and compact them using rank/select.

The bound must include input quantization, actual tensor/SFU accumulation behavior and extraction. A heuristic margin may still be a useful approximate algorithm, but it must not be labeled certified.


## Why it could work

The decision follows interval containment. Most objects far from the threshold can avoid expensive work while final answers remain exact. This is a way to compose different units according to uncertainty rather than one fixed arithmetic policy.

## Full cost and strongest baseline

Compare direct exact evaluation and an inexpensive integer/bitset prefilter. Include bound construction, ambiguity traffic and refinement scheduling. Input distributions nearτ can make almost every item ambiguous.

## Falsifier / rejection condition

Reject the exactness claim without a valid bound. Reject the performance idea if fallback and bookkeeping cost exceed work avoided, even when the fast stage has impressive throughput.

**Experiment:** E10 E11 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c15"></a>


# C15 — High/low precision expansion as a composite operator

> Build additional accuracy from multiple native products with an explicit residual.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** precision, tensor, expansion.
**Prerequisites:** M28 M09 R15. **Evidence:** S21 S20.

## Construction [H; reachability C/P]


Split A=Ah+Al and B=Bh+Bl into representable components. Compute AhBh+AhBl+AlBh and optionally AlBl. Omitting the last term leaves exact-algebra residual AlBl, with norm bound ||Al||||Bl|| for a compatible norm.

Actual output error also contains all input splitting, product accumulation and combination errors. Choose scales so the low component is meaningful and representable; a poorly scaled split may simply underflow.


## Why it could work

The expansion exposes more useful work to native half-input products while separating the accuracy budget into terms. It can be tuned by dropping or retaining a correction rather than assuming a nonexistent full-FP32 tensor instruction.

## Full cost and strongest baseline

Compare native FP32, compensated approaches and problem-specific reformulations. Three/four products, conversions and extra live fragments can exhaust registers or bandwidth. Conditioning determines whether the residual is acceptable.

## Falsifier / rejection condition

Reject when the actual numerical tests violate the promised bound, or when correction work and routing exceed the chosen conventional precision path.

**Experiment:** E10 E12 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c16"></a>


# C16 — Cancel intermediate transposes by composing ownership maps

> Keep data where the next instruction can already use it.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** fragments, layout, transpose, fusion.
**Prerequisites:** M25 M18 M04 R05. **Evidence:** S07 S22 S23.

## Construction [H; reachability C/P]


Write each producer and consumer layout as an explicit map from semantic coordinates to lane/register/shared positions. Compose the maps. If an intermediate canonicalization and subsequent retile are inverses, remove both and express the middle operation in the retained coordinates.

If only part of the maps cancel, route just the required subset. Replicated constants or a changed consumer tile may make the remaining exchange cheaper. Validate bijections and any intentional replication explicitly.


## Why it could work

A layout is an interface, not a cosmetic storage choice. Eliminating a store/barrier/load stage can save more than optimizing the arithmetic itself. Elementwise operations are often invariant under a shared permutation of their inputs and outputs.

## Full cost and strongest baseline

Count added address logic, shuffles and live registers. Direct accumulator compatibility is not guaranteed by matching matrix dimensions. Precision conversions can change the ownership and cost landscape.

## Falsifier / rejection condition

Reject when the fused representation creates spills, long dependencies or more expensive downstream access than the removed stages. Measure the full producer-to-consumer chain.

**Experiment:** E09 E04 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c17"></a>


# C17 — Operand-read hypergraph coloring

> Optimize how values reach instructions, not only where values are stored.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** register banks, reuse, SASS.
**Prerequisites:** M12 M13 R02 R10. **Evidence:** S04 S05 S11.

## Construction [H; reachability B; source-level C alternatives]


For a hot instruction sequence, record each distinct register read and any reuse-assisted read. Treat instructions as hyperedges over values. Search assignments or amortized copies that reduce repeated bank conflicts while preserving every def/use and dependency.

Use source restructuring first. Escalate to a pinned binary experiment only when it isolates a real compiler limitation. Keep a deterministic transformation and original binary for differential testing.


## Why it could work

Bank supply can limit an unchanged arithmetic sequence. Reuse removes pressure from the graph, so a globally sensible assignment may differ from a naïve “alternate all register numbers” rule.

## Full cost and strongest baseline

Include inserted moves, live-range extension, occupancy and conflicts introduced elsewhere. The empirical bank model is not a universal PTX contract. Compare equal instruction work and clocks before attributing a result.

## Falsifier / rejection condition

Reject any transformation without complete executable metadata/dependency validation. Reject the optimization if its local port gain disappears in the complete kernel.

**Experiment:** E04 E30. This composition has not been benchmarked on a V100 here.


---

<a id="c18"></a>


# C18 — A portfolio of useful pipeline work

> Interleave real subproblems that stress different resources.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** ILP, pipelines, latency hiding.
**Prerequisites:** M16 M08 M11 R14. **Evidence:** S01 S04.

## Construction [H; reachability C/P]


Factor a semantic stage into independently useful components: dense state mixing, integer support maintenance, future address generation, conversion and selected loads. Interleave them while respecting dependencies. Hold multiple independent accumulators only when they correspond to required outputs.

Compare isolated timings, serial composition and interleaved composition. Use resource-demand bounds to explain the result rather than adding all advertised peaks.


## Why it could work

Waiting on one dependency can leave another path able to do required work. Representations that expose independent metadata and payload computation can exploit this without changing the algorithm.

## Full cost and strongest baseline

Issue, register ports, HBM and power are shared. Extra register state can reduce eligible work. A nominally separate instruction family may use the same actual pipe on sm70.

## Falsifier / rejection condition

Reject when “overlap” merely adds work absent from the baseline, or when the shared resource becomes more congested and complete latency grows.

**Experiment:** E02 E03 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c19"></a>


# C19 — Manual latency hiding without importing cp.async

> Build a Volta pipeline from early loads, independent work, shared stages or DMA.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** prefetch, persistent, DMA, latency hiding.
**Prerequisites:** M15 M16 M19 M36 R06. **Evidence:** S01 S30 S15.

## Construction [H; reachability C/P]


Issue ordinary future loads early into registers while computing on current data. For block reuse, stage into shared memory and publish at a valid phase boundary. Alternatively, let a copy engine fill a later buffer under supported stream/event ordering.

A loader-warp role is an option, not a requirement. Compare it to each compute warp prefetching its own next work. Choose buffer depth from latency, bandwidth and live-state cost.


## Why it could work

The schedule creates independent useful work between request and use. It supplies the purpose of an asynchronous pipeline without claiming later cp.async/mbarrier semantics exist on Volta.

## Full cost and strongest baseline

Early loads consume registers and request slots. Additional buffers consume memory and synchronize. Copy and compute share HBM; specialized warps may sit idle under skew.

## Falsifier / rejection condition

Reject if the pipeline cannot prove producer progress/visibility, if stalls simply move to another boundary, or if register/buffer pressure costs more than the hidden latency.

**Experiment:** E03 E06 E16 E17. This composition has not been benchmarked on a V100 here.


---

<a id="c20"></a>


# C20 — Owner-compute instead of remote pointer chasing

> Send a compact question to where the large state already lives.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** NVLink, graph, owner compute, communication.
**Prerequisites:** M34 M35 M30 R06 R07. **Evidence:** S02 S25 S26.

## Construction [H; reachability C/P]


Compare three implementations of the same query: requester gathers remote data; requester stages a bulk region and computes; or a resident owner service receives a compact descriptor, computes locally and returns a reduced answer. The owner can cache support/coefficient state across many queries.

The service is a software queue plus a schedulable kernel, not a hardware remote-function call. Batch compatible requests and keep reply ownership explicit. Use direct remote loads for tiny control fields only when their contract and latency make sense.


## Why it could work

Communication cost can fall from many irregular payload reads to a descriptor and a small result. This exploits information reduction rather than only higher link bandwidth.

## Full cost and strongest baseline

Include enqueue, publication, service admission, load balance, completion and reply latency. The owner competes with its local work for HBM/SMs. Direct pull may win for rare small reads; staging may win for repeated dense reuse.

## Falsifier / rejection condition

Reject when service overhead exceeds payload savings, when imbalance dominates, or when waiting actors can starve the service producer. No remote-cache assumption is required for the comparison.

**Experiment:** E18 E19 E16 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c21"></a>


# C21 — Transmit support or deltas instead of dense state

> Choose the information boundary before choosing a faster transfer.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** NVLink, compression, support, delta.
**Prerequisites:** M06 M34 M35 R07. **Evidence:** S02 S25 S26.

## Construction [H; reachability C/P]


When a receiver already owns a valid base state, send changed positions plus values, or a support/frontier mask when only activity is needed. Include an epoch/base identifier and an explicit reset/resynchronization path. Bitplanes can be the wire format rather than an internal-only optimization.

Use density thresholds to switch to dense transfer when sparse metadata becomes larger. Keep the sparse and dense paths semantically identical; ordering and duplicate behavior must be defined.


## Why it could work

Only new information needs to cross the link. A word-level support representation can collapse many tiny signals into one payload and support direct receiver-side routing.

## Full cost and strongest baseline

Include detection, encoding, base-state maintenance, decoding and lost coalescing. A compressed transfer is not useful if the receiver immediately reconstructs an equally expensive dense object for every step.

## Falsifier / rejection condition

Reject when state ownership/epoch correctness is unproved, when changes are too dense, or when maintaining deltas costs more than moving the original representation.

**Experiment:** E13 E19 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c22"></a>


# C22 — A published ring with explicit reuse epochs

> Build the synchronization protocol before optimizing the flag instruction.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** queue, semaphore, publication, progress.
**Prerequisites:** M29 M31 M35 R06. **Evidence:** S17 S25 S30 S42.

## Construction [H; reachability C/P]


Model each slot through free→reserved→published→consumed→reusable. Reservation grants a writer exclusive space; payload writes precede release publication. A reader acquire-observes the matching epoch before reading, and publishes reuse only after finishing. Bound counter distance across wraparound.

Use a separate validity/sequence word when necessary to distinguish reused slots. A group reservation can allocate several slots, but completion of the group still requires its own rule. Define shutdown, cancellation and backpressure.


## Why it could work

The state machine prevents readers from confusing reservation with completed payload and writers from overwriting unconsumed data. It can be embodied by supported atomics or stream-memory operations at the correct scope.

## Full cost and strongest baseline

Compare established device/peer queue protocols. Count polling traffic, fences, slot padding and latency tails. A command wait may save an SM but can introduce a submission-graph dependency invisible to CUDA.

## Falsifier / rejection condition

Reject without a participation, visibility and progress proof. Tests are only falsifiers. In particular, a consumer occupying all producer resources is invalid regardless of how fast the atomic is.

**Experiment:** E15 E19 E22. This composition has not been benchmarked on a V100 here.


---

<a id="c23"></a>


# C23 — Topology-aware ownership and dual host ingress

> Align where bytes are produced, stored and consumed instead of forcing one uniform path.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** NUMA, PCIe, NVLink, ownership.
**Prerequisites:** M43 M36 M34 R07. **Evidence:** S30 S33 S36.

## Construction [H; reachability C/P]


Discover actual directed paths and host roots. Partition produced data so CPU-local pinned pages feed the corresponding GPU owner. Place each hot operator near its dominant state and transfer reduced boundary information. Compare both ingress paths concurrently to isolated transfers.

A pair spanning NUMA nodes can have useful independent input capacity when the application can produce data locally. This is a workload/topology opportunity, not proof that every x8 pair behaves that way.


## Why it could work

The representation acquires a physical home, which can remove unnecessary cross-socket traffic and remote GPU loads. Different boundaries can use different units of work without a meta-device abstraction.

## Full cost and strongest baseline

Count producer relocation, page placement, PCIe DMA and CPU-interconnect traffic. Thread affinity alone does not prove page locality. Simultaneous paths may share hidden roots or HBM service.

## Falsifier / rejection condition

Reject when topology inventory disproves independence, when data is inherently produced on the other node, or when boundary traffic overwhelms the locality benefit.

**Experiment:** E20 E21 E35. This composition has not been benchmarked on a V100 here.


---

<a id="c24"></a>


# C24 — Monotone atomic fixed-point computation

> For the right algebra, duplicates and execution order can stop being correctness problems.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** atomics, dataflow, graph, fixed point.
**Prerequisites:** M29 M21 M30 R06. **Evidence:** S03 S30.

## Construction [H; reachability C/P]


Choose a state domain with an associative, commutative, idempotent merge and a monotone update. Examples include accumulating reachability bits by OR or suitable bounded min/max propagation. A successful change can enqueue affected neighbors; duplicate proposals merge harmlessly.

State clearly whether the domain is finite-height or otherwise convergent, and how fairness ensures relevant updates occur. Termination must account for queued and in-flight work, not merely an empty local frontier.


## Why it could work

Idempotence can trade rigid lockstep for redundant but harmless work. Atomics embody the merge itself rather than only protecting an unrelated critical section. This is a mathematical change to the coordination problem.

## Full cost and strongest baseline

Compare synchronized frontiers and locally aggregated proposals. Duplicate work, hot targets and termination detection can erase the gain. Floating addition and overwrite are not idempotent, so ordinary dynamical integration does not automatically qualify.

## Falsifier / rejection condition

Reject if the update is non monotone, if stale state changes the fixed point, or if progress/termination is not established. A convergent equation alone is not a schedulable implementation.

**Experiment:** E01 E14 E15 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c25"></a>


# C25 — A resident micro service with a finite operator palette

> Preserve hot computational state while consuming compact task descriptions.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** persistent, scheduler, FSM, latency.
**Prerequisites:** M30 M15 M14 M17 R06. **Evidence:** S30 S01.

## Construction [H; reachability C/P]


Select a small family of operations sharing useful register/shared state. A long-lived executor consumes bounded descriptors, groups compatible work and emits completion records. Use local batching before global work stealing. Define stop/drain and descriptor lifetime.

An operator palette can be a handful of graph/state transforms, not a general virtual machine. Keep rare complex cases on another path so the hot executor remains small.


## Why it could work

Launch and state reload costs can be amortized across many tiny tasks. The scheduler becomes part of the data representation: compact task IDs identify already resident coefficients and layouts.

## Full cost and strongest baseline

Compare graphs, proper batching and fused kernels. Queue traffic, dispatch divergence, idle reservations and instruction footprint count. A resident kernel can reduce available capacity for its own producer.

## Falsifier / rejection condition

Reject when tasks are already large enough to amortize launches, when the palette fragments control excessively, or when progress depends on unspecified concurrent scheduling.

**Experiment:** E16 E32 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c26"></a>


# C26 — Component remapping in the copy engine

> Investigate moving a fixed record format directly into its consumer representation.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** DMA, format, remap, non-SM.
**Prerequisites:** M37 M36 R09. **Evidence:** S12 S15.

## Construction [H; reachability K]


Use the documented copy-class component controls as a research target: select source components, insert supported constants or suppress selected outputs while copying between supported pitched/linear layouts. Begin with a small fixed-width record transformation whose CPU reference is unambiguous.

Establish a valid owned driver/channel route and all field units before issuing anything. Public DMA plus a shader transform remains the initial executable baseline. Existing UVM fill remapping is evidence of the machinery, not of a complete general-purpose public API.


## Why it could work

If reachable at acceptable cost, the engine could transform data while SMs perform other useful work. Removing a separate read/write formatting pass could matter more than saving arithmetic.

## Full cost and strongest baseline

Compare a fused SM copy/transform and ordinary copy+transform. Include command construction, launch latency and shared HBM contention. Component remap is restricted; it is not arbitrary AoS↔SoA, gather or permutation.

## Falsifier / rejection condition

Reject if the required layout is not expressible, if a safe reachable interface cannot be established, or if setup and interference exceed the saved pass.

**Experiment:** E27 E17. This composition has not been benchmarked on a V100 here.


---

<a id="c27"></a>


# C27 — Command-engine completion arithmetic

> Use a non-SM actor for narrow progress-state operations.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** semaphore, DMA, control, non-SM.
**Prerequisites:** M38 M31 R09 R06. **Evidence:** S12 S15 S17.

## Construction [H; reachability K; public C alternatives]


The pinned Volta HAL already emits semaphore release, increment and timestamp commands with payload transfer disabled. The copy-class header additionally names unsigned/signed reduction operations such as MIN, MAX, XOR, AND, OR and ADD. Treat the observed HAL forms and the broader declared menu as different evidence strengths.

A candidate pipeline can publish a phase count or update a control word without launching a tiny shader. Establish exact INC/DEC threshold/wrap semantics, flush behavior, target scope and command ordering before using them. These operations act on the semaphore target, not every element of a buffer.


## Why it could work

The copy engine is demonstrably capable of control work independent of bulk copy. A bounded control sequence might spare SM residency or avoid a kernel boundary while preserving data-engine progress.

## Full cost and strongest baseline

Compare public stream memory operations, events and a tiny kernel. Deeper command submission can cost more than the saved work. Different engine timestamps are not automatically comparable with GPU global timer or another device.

## Falsifier / rejection condition

Reject any “general DMA ALU” interpretation. Reject if only a private unsafe route is available, if ordering cannot be proved, or if the whole pipeline fails to beat supported alternatives.

**Experiment:** E28 E22. This composition has not been benchmarked on a V100 here.


---

<a id="c28"></a>


# C28 — Dependent QMDs as a bounded dataflow experiment

> Explore the launch front end only after public graph replay is a measured baseline.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** QMD, launch, dataflow, driver.
**Prerequisites:** M39 M38 M33 R09 R06. **Evidence:** S27 S13 S40.

## Construction [S; reachability K]


Start from two finite kernels with known buffers and one explicit dependency. Investigate documented descriptor dependency/release fields and queue ownership. Determine address units, resource fields, reference counts, visibility and completion semantics from implementation evidence before constructing commands.

Only after that minimal case would circular queues or longer bounded phases be meaningful experiments. Do not rewrite live CUDA-owned descriptors or equate an SM-mask field with ordinary CUDA affinity.


## Why it could work

The header proves richer control objects exist below the familiar launch API. It leaves open whether a useful restricted dataflow schedule can reduce CPU/SM orchestration overhead on this platform.

## Full cost and strongest baseline

Public graphs and batched launches are the strongest baselines. Setup, firmware validation and driver ownership can dominate. No arbitrary self-modifying runtime or cross GPU work migration is established.

## Falsifier / rejection condition

Reject if operational contracts remain unknown, if safety requires unsupported ownership violations, or if the minimal case cannot outperform public graph replay at equal semantics.

**Experiment:** E29 E32. This composition has not been benchmarked on a V100 here.


---

<a id="c29"></a>


# C29 — A doubled virtual ring without duplicate payload

> Use two legal views of one backing region to remove split-window handling.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** VMM, alias, ring, addressing.
**Prerequisites:** M40 R08 R06. **Evidence:** S18 S31.

## Construction [H; reachability C/P]


Reserve a2N virtual interval and investigate mapping the sa meN backing bytes into both halves. A window of length≤N starting in the first half could then be virtually contiguous even when it wraps the physical ring. Align N to required granularity and establish the legal alias/cache contract.

Keep producer/consumer ownership and epoch synchronization exactly as explicit as in a conventional ring. This transformation changes addressing, not concurrency semantics.


## Why it could work

Virtual address layout can remove modulo or two-segment handling without copying the payload. It can be useful for repeated windows when the consumer accepts the mapped view directly.

## Full cost and strongest baseline

Compare two-pointer windows and simple modulo, which may already compile cheaply. Mapping setup, VA footprint, TLB behavior and any coherence restrictions count. Aliasing is not assumed safe merely because both mappings succeed.

## Falsifier / rejection condition

Reject when the installed V MM contract cannot support the intended use, when concurrent aliases lack a proof, or when translation cost exceeds saved address work.

**Experiment:** E23 E08. This composition has not been benchmarked on a V100 here.


---

<a id="c30"></a>


# C30 — Translation-policy zoning on an ATS platform

> An address-space boundary can be an algorithmic placement boundary.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** ATS, VMM, POWER9, policy.
**Prerequisites:** M41 M42 R08. **Evidence:** S16 S28 S29.

## Construction [S; reachability K/F]


The Volta MMU implementation exposes NO_ATS policy at a512 MB directory-region scale. On a compatible ATS platform, investigate grouping allocations by desired translation/fault behavior so CPU translation does not defeat a GPU-managed policy.

Separate immutable remote data, migra table state and strict GPU-resident control. First establish which controls are actually exposed by the installed driver; ordinary CUDA cannot be assumed to edit these bits.


## Why it could work

The existing implementation shows that address-space placement can affect translation policy, not merely naming. Coarse allocation zones might avoid unintended behavior or reduce policy conflicts.

## Full cost and strongest baseline

Compare normal managed advice, prefetch and explicit placement. Large granularity wastes flexibility; fault/migration delay can dwarf kernel work. This idea is not transferable to an x86 host simply because it has V100NVLink.

## Falsifier / rejection condition

Reject without the required platform/interface, or when the policy problem can be solved more cheaply through supported placement controls.

**Experiment:** E24 E35. This composition has not been benchmarked on a V100 here.


---

<a id="c31"></a>


# C31 — Texture interpolation as a nonlinear circuit element

> Tabulate a smooth function and let the sampler supply part of the arithmetic.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** nonlinear, texture, SFU, approximation.
**Prerequisites:** M23 M10 R15. **Evidence:** S30 S03.

## Construction [H; reachability C/P]


Tabulate a smooth scalar function over bounded intervals and use a documented texture filtering path to interpolate. For ideal linear interpolation on interval width h, an error bound is h²·max|f″|/8. Add sample quantization, coordinate/filter precision and output conversion errors to obtain the actual contract.

Use nonuniform regions or explicit exceptional paths around singularities/discontinuities. Multi-dimensional tables can express coupled approximate updates when their size and sampling contract fit.


## Why it could work

The sampler becomes a small lookup-and-interpolation machine, not merely an image accessor. It can replace a longer arithmetic sequence if the table is reused and the error budget permits.

## Full cost and strongest baseline

Compare S FUse ed+refinement, polynomials and cached table+manual interpolation. Include creation/update, traffic and boundary handling. A huge table can replace arithmetic with worse memory pressure.

## Falsifier / rejection condition

Reject if the error bound cannot include real hardware filter behavior, if the function range is unsuitable, or if table traffic/setup exceeds the arithmetic saved.

**Experiment:** E26 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c32"></a>


# C32 — A coarse self-adapting kernel policy

> Use a small validated choice set and make observation cost explicit.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** adaptation, counters, policy, latency.
**Prerequisites:** M46 M42 M47 R11 R12. **Evidence:** S34 S35 S36 S29.

## Construction [H; reachability C/P]


Choose among several already-correct representations or tile policies using epoch duration, queue depth, density or supported counters. Apply hysteresis and a minimum residence time. Switch only when q·estimated_saving exceeds observation+switch+repack cost plus an uncertainty margin, where q is expected remaining reuse.

Maintain a fixed-policy control and log why a choice changed. Use the cheapest signal that predicts the relevant resource bottleneck.


## Why it could work

Workload phases can change the best representation. Feedback can exploit this without putting a heavyweight optimizer in every warp. The policy selects among verified kernels; it does not invent unsafe synchronization at runtime.

## Full cost and strongest baseline

Include lag, noise, cold state and measurement perturbation. Some profilers replay kernels and are unsuitable as live feedback. A tiny density heuristic may beat a rich counter model.

## Falsifier / rejection condition

Reject when adaptation has worse regret than a fixed policy, when measurement dominates, or when oscillation repeatedly destroys locality.

**Experiment:** E25 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c33"></a>


# C33 — Steady-state scheduling under power and thermal limits

> Optimize useful sustained work rather than cold instantaneous utilization.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** power, thermal, scheduling.
**Prerequisites:** M52 M46 R11 R13. **Evidence:** S02 S36.

## Construction [H; reachability C/P]


Measure several equal-work schedules: maximal overlap, phase interleaving and topology redistribution. Keep allowed power limits unchanged. Observe stable clocks, temperature, throughput and energy per result after thermal settling.

A coarse policy may choose a different schedule when one module or resource remains throttled. This is software work placement, not voltage/firmware modification.


## Why it could work

Compute, memory and fabric compete within physical budgets. A schedule with less instantaneous overlap could sustain a better useful rate if it avoids a persistent shared limit; the opposite is equally possible.

## Full cost and strongest baseline

Compare at identical outputs and environment. Longer wall time can increase energy even at lower power. Sensor averaging and neighbor activity can hide short phases. Cold startup comparisons are inadequate.

## Falsifier / rejection condition

Reject if the effect disappears at steady state, if it merely reduces work/accuracy, or if management overhead outweighs any sustained gain.

**Experiment:** E33 E25. This composition has not been benchmarked on a V100 here.


---

<a id="c34"></a>


# C34 — Phase-factored circuits instead of a giant mega kernel

> Keep the hot instruction and register working set small enough to be useful.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** instruction cache, persistent, phases.
**Prerequisites:** M17 M30 M33 R02. **Evidence:** S04 S05 S30.

## Construction [H; reachability C/P]


Split a broad rule palette into a small hot circuit and infrequent exceptional paths. Factor repeated instruction sequences or use a compact resident interpreter only for the shared core. Group tasks by operator/shape to reduce divergent dispatch.

Compare a fully unrolled version, a factored version, graphs and separate kernels. Keep semantic work and data reuse comparable.


## Why it could work

Instruction fetch and live register state are real working sets. Removing repeated code or rare branches can improve the useful machine even when it adds a small dispatch operation.

## Full cost and strongest baseline

Phase boundaries can force data stores, barriers or lost compiler optimization. A smaller binary is not automatically faster. Count operand reloads and hand off cost along with instruction cache behavior.

## Falsifier / rejection condition

Reject if factoring merely moves cost into dispatch/state material i zat i on or if the original instruction footprint was not a bottleneck.

**Experiment:** E02 E30 E32 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c35"></a>


# C35 — Delete metadata through positional identity

> Use lane, bit or local slot as an address when both ends share the mapping.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** metadata, layout, routing, compression.
**Prerequisites:** M02 M04 M14 R01. **Evidence:** S03 S10.

## Construction [H; reachability C/P]


Give a compact local object a stable positional identity: lane for vertex, bit for support member, register slot for small state component or block local position for coefficient. Define an explicit reversible map to external IDs only at boundaries.

Rank/select turns a mask into compact indexes when a boundary needs them. Avoid storing an index beside every value if the execution position already identifies it.


## Why it could work

The representation removes redundant information and its loads, address arithmetic and cache footprint. This is often a larger optimization than accelerating the metadata calculation itself.

## Full cost and strongest baseline

Mapping maintenance costs grow when objects are frequently reordered or deleted. Padding and boundary maps count. Physical SM IDs and transient warp IDs are not a stable external naming system.

## Falsifier / rejection condition

Reject when reorganization requires rebuilding maps every step, or when positional assumptions become hidden correctness dependencies that consumers cannot honor.

**Experiment:** E05 E13 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c36"></a>


# C36 — Compose lane, bank and fragment permutations

> Optimize the entire path rather than one attractive memory layout.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** layout, transpose, shared, fragments.
**Prerequisites:** M18 M25 M22 R05. **Evidence:** S22 S23 S30.

## Construction [H; reachability C/P]


Represent each layout as a mapping between semantic coordinates and physical positions. Choose a producer layout that coalesces global loads, then a shared swizzle and fragment assignment whose compositions minimize the exchanges required by later operators.

Test the composite map for coverage, bijection or intentional replication. An inverse pair of transposes may disappear. A mapping that optimizes one stage but destroys the next is not globally good.


## Why it could work

Permutation composition is exact algebra on indexes. It can eliminate movement rather than merely making each movement faster. Ownership maps are reusable interfaces between kernels or fused stages.

## Full cost and strongest baseline

Count address instructions, padding, bank conflicts, register pressure and final output order. Some maps are cheap only at fixed shape; dynamic shapes need fallbacks. Actual physical HBM hashes are not assumed known.

## Falsifier / rejection condition

Reject when extra index arithmetic or live state exceeds the removed traffic, or when the mapping relies on undefined WMMA fragment internals.

**Experiment:** E01 E06 E09 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c37"></a>


# C37 — Carry-save trees for bitset threshold queries

> Count many masks without expanding each bit to a scalar counter.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** bitsets, threshold, reduction, Boolean.
**Prerequisites:** M01 M02 M06 R15. **Evidence:** S03 S08.

## Construction [H; reachability C/P]


Combine three equal-weight planes a, b, c into sum=a^b^c at the same weight and carry=majority(a, b, c) at twice the weight. Repeat as a carry-save tree until one plane remains per weight. For each bit position the weighted planes encode how many in put masks contain it.

Evaluate a threshold directly on those planes, or compute total population as Σ_j 2^j·popcount(plane_j). The two outputs answer different questions: per-position multiplicity versus aggregate count.


## Why it could work

Carry remains an explicit plane, so unrelated bit positions never interfere. Many scalar counters are replaced by a network of word gates. Threshold ing can avoid full binary decode.

## Full cost and strongest baseline

Compare serial popcounts for an aggregate count and packed/scalar counts for per-position results. Plane count, register pressure and threshold circuit cost matter. A simple aggregate may not justify the tree.

## Falsifier / rejection condition

Reject when only one total count is needed and direct POPC reduction wins, or when the number of in put planes exhausts useful register capacity.

**Experiment:** E01 E13 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c38"></a>


# C38 — Empirical conflict maps as placement hints

> Exploit a repeatable memory conflict without pretending its physical cause is fully known.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** HBM, L2, placement, measurement.
**Prerequisites:** M22 M21 R03 R12. **Evidence:** S04 S30.

## Construction [H; reachability C/P]


Measure address groups that contend under controlled parallel access. Use the result to permute independent state blocks or separate hot counters. Recheck after reallocations, page policy or driver changes.

The map is an empirical performance hint tied to allocation/conditions. Correctness must not depend on a supposed channel bit orL2slice. Keep a conventional layout fallback.


## Why it could work

An optimizer can exploit stable observable interference even before fully reconstructing the hash. This applies the same principle as bank-aware layout at a less documented scale.

## Full cost and strongest baseline

Control cache/TLB effects, request concurrency and alignment so the experiment discriminates possible causes. Training the map is a preprocessing cost. An improvement may come from translations rather than HBM distribution.

## Falsifier / rejection condition

Reject if the effect does not replicate across held-out patterns, if it disappears under real concurrency, or if retraining costs more than there used gain.

**Experiment:** E07 E08 E20 E39. This composition has not been benchmarked on a V100 here.


---

<a id="c39"></a>


# C39 — A representation-changing search procedure

> For each new primitive, construct alternatives that move the problem to a different kind of machinery.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** design methodology, creative search, performance.
**Prerequisites:** R00 R11 R14 R15. **Evidence:** original synthesis; see linked mechanisms.

## Construction [H; reachability C/P]


Write the exact semantic operation, valid in put domain, output contract and required reuse. Then create at least three candidates: a strong conventional implementation; a representation-changing implementation; and an implementation using a different resource or information boundary.

Examples: CSR traversal versus register bitset graph versus owner-compute query; scalar transition versus bit-sliced circuit versus table lookup; SIMT transform versus tensor fragment versus precomputed basis routing. These are competing experiments, not a compulsory architecture.


## Why it could work

The procedure avoids optimizing a poor representation indefinitely. Every candidate is grounded in a primitive and a complete cost model, so extreme ideas can be retained without being promoted to facts.

## Full cost and strongest baseline

Track encode/decode, lifetime, precision, communication, progress, code size and strongest baseline. Prove exactness or declare approximation. Measure whole workload after isolated mechanisms. A new resource is not inherently a win.

## Falsifier / rejection condition

Reject candidates by explicit falsifiers and retain the reason in the ledger. Do not erase unconventional directions merely because the first shape failed, nor keep them alive by omitting their real cost.

**Experiment:** E38 E39. This composition has not been benchmarked on a V100 here.


---

<a id="e00"></a>


# E00 — Inventory and capability gates

> What exact machine and reachable feature set do these experiments target?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, inventory, and, capability, gates.
**Prerequisites:** R12. **Evidence:** S32 S36 S42.

**Question:** What exact machine and reachable feature set do these experiments target?

**Minimal setup:** Run the supplied read-only Driver API probe plus UUID/BDF, topology, PCIe, NUMA and link-state inspection. Save raw outputs before allocating benchmark buffers.

**Sweep:** Every device and ordered pair; compiler and driver versions separately; idle and steady-load telemetry.

**Discriminating observation:** A capability matrix that distinguishes physical identity, peer access, native atomics, VMM, managed memory and stream operations.

**Baseline:** No performance baseline; compare reported inventory to assumptions in a candidate design.

**Confounders / correctness:** Device ordinals can change. A supported flag is not an achieved-performance measurement. Do not reset, enable peers or change clocks as part of inventory.

**Access gate:** Public read-only queries; errors must be retained, not treated as false or zero.

**Related:** R01 R07 R10 R13.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e01"></a>


# E01 — Algebra and encoding checks

> Are the proposed word circuits and layout equations actually equivalent?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, algebra, and, encoding, checks.
**Prerequisites:** R12. **Evidence:** original synthesis; see linked mechanisms.

**Question:** Are the proposed word circuits and layout equations actually equivalent?

**Minimal setup:** Run tools/semantic_checks.py. Extend with exhaustive small truth tables and deterministic randomized references for any new composition.

**Sweep:** Partial groups, widths, boundary symbols, overflow guards and all small finite states.

**Discriminating observation:** Exact agreement for Boolean/routing identities and deliberate failure of insufficient-guard negative controls.

**Baseline:** Simple integer/list reference implementations.

**Confounders / correctness:** CPU success does not test GPU rounding, collective participation, compiler lowering or memory ordering.

**Access gate:** CPU only; the supplied suite is actually run and logged in this package.

**Related:** C00 C01 C02 C03 C05 C06 C07 C37.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e02"></a>


# E02 — Instruction latency versus throughput

> Which dependency and resource limits govern an exact sm70 instruction form?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, instruction, latency, versus, throughput.
**Prerequisites:** R12. **Evidence:** S01 S04 S05 S03.

**Question:** Which dependency and resource limits govern an exact sm70 instruction form?

**Minimal setup:** Create one true dependent chain and a separate multi-accumulator kernel. Consume results; inspect native SASS and subtract bounded measurement/loop overhead.

**Sweep:** Chain length, independent chains, warps, unrolling, operand forms and register pressure.

**Discriminating observation:** A serial latency estimate distinct from independent service throughput and saturation.

**Baseline:** Equivalent scalar operation and empty/loop controls.

**Confounders / correctness:** Compiler folding, clock changes, instruction-cache effects and added spills can masquerade as instruction latency.

**Access gate:** Public CUDA/PTX initially; B-level variants only after binary validation.

**Related:** R02 M16 M17 M47.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e03"></a>


# E03 — Cross-pipeline interference

> Can two useful operation families overlap without saturating another shared resource?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, cross-pipeline, interference.
**Prerequisites:** R12. **Evidence:** S01 S04 S35.

**Question:** Can two useful operation families overlap without saturating another shared resource?

**Minimal setup:** Time each family alone, serially combined and interleaved at equal semantic work. Preserve enough independent operands to expose overlap.

**Sweep:** INT/FP/tensor/conversion/load mixes; relative work ratios; live-register budget.

**Discriminating observation:** Combined critical time closer to a maximum than a sum only where genuine overlap exists; counters explain new bottlenecks.

**Baseline:** Best isolated and serial schedules, not an intentionally poor ordering.

**Confounders / correctness:** Shared issue, register ports, HBM and power; extra work invalidates the comparison.

**Access gate:** Public/PTX forms; no unsupported later-architecture instructions.

**Related:** C18 C19 M16 R14.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e04"></a>


# E04 — Register bank and operand-reuse effects

> Does operand delivery limit this hot sequence?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, register, bank, and, operand-reuse, effects.
**Prerequisites:** R12. **Evidence:** S04 S05 S11.

**Question:** Does operand delivery limit this hot sequence?

**Minimal setup:** Compare semantically identical schedules with controlled operand assignment/reuse. Preserve original cubin and exact transformation.

**Sweep:** Register parity, source reuse, inserted amortized copies and independent instruction spacing.

**Discriminating observation:** Repeatable changes tied to distinct bank reads rather than occupancy or arithmetic changes.

**Baseline:** Original compiler output and a dependency-matched schedule.

**Confounders / correctness:** Changed live ranges, spills, resource metadata and clock state. Source names do not identify physical registers.

**Access gate:** B-level edits require validated tools and complete dependency/resource preservation.

**Related:** C17 M12 M13.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e05"></a>


# E05 — Warp routing, matching and lookup

> When do register exchange and equality grouping beat memory-based structures?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, warp, routing, matching, and, lookup.
**Prerequisites:** R12. **Evidence:** S03 S08 S10.

**Question:** When do register exchange and equality grouping beat memory-based structures?

**Minimal setup:** Implement shuffle tables, match-group reservations and mask rank/select with explicit participation. Validate every small index/group shape first.

**Sweep:** Table size, query uniformity, key cardinality, active masks, payload width and reuse.

**Discriminating observation:** Break-even surfaces for register/shared/constant lookup and grouped atomics.

**Baseline:** Cached global/shared tables and one-atomic-per-lane plus established aggregation.

**Confounders / correctness:** Inactive source lanes, undefined selected values, multiword selection and hidden spills.

**Access gate:** Use valid synchronized primitives; do not use incidental activemask as logical membership.

**Related:** C03 C04 M02 M04 M05.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e06"></a>


# E06 — Shared banks and phase pipelines

> Which layout and synchronization phase actually reduces complete movement cost?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, shared, banks, and, phase, pipelines.
**Prerequisites:** R12. **Evidence:** S01 S30.

**Question:** Which layout and synchronization phase actually reduces complete movement cost?

**Minimal setup:** Construct controlled broadcast/conflict patterns and producer-consumer tile stages. Keep the semantic data permutation fixed.

**Sweep:** Stride, swizzle, padding, payload width, barrier placement and shared carveout.

**Discriminating observation:** Producer-to-consumer timing and conflict behavior, not only a fast standalone store.

**Baseline:** Shuffles for small exchanges and conventional shared tiling.

**Confounders / correctness:** Same word broadcast differs from distinct words in one bank. All required participants must reach barriers.

**Access gate:** Public shared-memory/barrier contracts; no later mbarrier assumptions.

**Related:** C16 C19 C36 M18 M19.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e07"></a>


# E07 — Cache and transaction accounting

> What fraction of traffic carries useful information, under which reuse conditions?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, cache, and, transaction, accounting.
**Prerequisites:** R12. **Evidence:** S04 S30 S35.

**Question:** What fraction of traffic carries useful information, under which reuse conditions?

**Minimal setup:** Use both independent streaming accesses and dependent pointer chains. Separate read/write, warm/cold and cache forms.

**Sweep:** Working set, stride, alignment, active lanes, concurrency and metadata/payload separation.

**Discriminating observation:** Latency/throughput/sector signatures consistent with a stated cache or transaction explanation.

**Baseline:** Contiguous useful-byte loads and a deliberately scattered control.

**Confounders / correctness:** TLBs, page allocation, compiler elimination and profiler cache flushing. A plateau alone does not prove a cache level.

**Access gate:** Public/PTX memory operations with legal cache semantics.

**Related:** R03 M20 M21 M22 C38.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e08"></a>


# E08 — Translation working sets and pages

> Is the irregular workload limited by translation rather than data bandwidth?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, translation, working, sets, and, pages.
**Prerequisites:** R12. **Evidence:** S04 S16 S31.

**Question:** Is the irregular workload limited by translation rather than data bandwidth?

**Minimal setup:** Hold useful bytes constant while changing page footprint and traversal order. Record VMM allocation settings separately from observed translation behavior.

**Sweep:** Page count, stride, allocation method, reuse and concurrent requests.

**Discriminating observation:** Performance changes with translation footprint that remain after data-cache controls.

**Baseline:** Page-local traversal and conventional contiguous allocation.

**Confounders / correctness:** VMM granularity is not automatically TLB page size; VA patterns do not directly reveal physical channel bits.

**Access gate:** Only supported allocation/advice/VMM interfaces; no direct PTE modification.

**Related:** R08 M40 C38.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e09"></a>


# E09 — MMA lane and register ownership

> Does the explicit sm70 fragment mapping match the compiled instruction?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, mma, lane, and, register, ownership.
**Prerequisites:** R12. **Evidence:** S03 S22 S23.

**Question:** Does the explicit sm70 fragment mapping match the compiled instruction?

**Minimal setup:** Use one-hot/basis inputs and uniquely labeled accumulators. Store raw per-lane outputs before any canonicalizing wrapper.

**Sweep:** Each lane, fragment element, group, row/column form and accumulator type separately.

**Discriminating observation:** Full coordinate coverage and exact expected ownership for the tested explicit PTX form.

**Baseline:** CPU coordinate map and scalar small matrix multiplication.

**Confounders / correctness:** Opaque WMMA layouts are not the explicit PTX contract; all required lanes execute the instruction.

**Access gate:** Compile supported sm70 forms and inspect SASS before interpreting output.

**Related:** R05 M24 M25 C10 C16.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e10"></a>


# E10 — Tensor numerical fingerprint

> Which target-specific rounding and range properties matter to an encoding?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, tensor, numerical, fingerprint.
**Prerequisites:** R12. **Evidence:** S20 S21 S03.

**Question:** Which target-specific rounding and range properties matter to an encoding?

**Minimal setup:** Use targeted exponent gaps, cancellation, ties, subnormals, zeros, large bounded counts and high/low expansions; retain exact references where possible.

**Sweep:** Operand placement, sign, accumulator magnitude, contraction length and conversion order.

**Discriminating observation:** A numerical feature table, not only mean error on random matrices.

**Baseline:** Exact integer/rational reference plus explicitly specified scalar floating evaluation orders.

**Confounders / correctness:** Input conversion can dominate; equality on easy nonnegative cases does not prove arbitrary FMA equivalence.

**Access gate:** No claim of exact tensor counting or certified filtering before this gate and a bound.

**Related:** R15 C11 C14 C15 M28.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e11"></a>


# E11 — Tensor versus bitset intersections

> When do many shared overlap queries repay numeric expansion?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, tensor, versus, bitset, intersections.
**Prerequisites:** R12. **Evidence:** S19 S20 S08.

**Question:** When do many shared overlap queries repay numeric expansion?

**Minimal setup:** Compute identical intersection counts or threshold decisions with packed AND+POPC, DP4A and supported tensor tiles.

**Sweep:** Universe length, query count, reuse, density, tile padding and requested output sparsity.

**Discriminating observation:** Whole-operation crossover including encode/decode and numerical validation.

**Baseline:** Strong packed-bitset implementation with cached cardinalities.

**Confounders / correctness:** Computing a dense answer matrix that the application does not need is not equal useful work.

**Access gate:** Counts must pass E10 within a proved or conservatively validated bounded domain.

**Related:** C11 C14 M26.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e12"></a>


# E12 — Tensor circuits versus structured SIMT

> Does a small transform benefit from MMA once routing is included?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, tensor, circuits, versus, structured, simt.
**Prerequisites:** R12. **Evidence:** S19 S24 S22.

**Question:** Does a small transform benefit from MMA once routing is included?

**Minimal setup:** Compare prefix, reduction, Hadamard/stencil or butterfly components with direct shuffle/add circuits and tensor implementations.

**Sweep:** Number of simultaneous transforms, coefficient reuse, fragment-resident input/output and precision.

**Discriminating observation:** The regime where native fragments and reuse beat fewer structured SIMT operations.

**Baseline:** Hand-structured shuffle/add implementation and suitable library path.

**Confounders / correctness:** Floating summation order, zero padding, normalization and extraction must be equivalent or bounded.

**Access gate:** Use verified fragment mapping and supported sm70 formats.

**Related:** C10 C12 C13 C15.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e13"></a>


# E13 — Representation crossover

> How many uses repay bitplanes, packing or a changed numerical domain?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, representation, crossover.
**Prerequisites:** R12. **Evidence:** S08 S09 S03.

**Question:** How many uses repay bitplanes, packing or a changed numerical domain?

**Minimal setup:** Implement encoding, steady-state operators and decoding as separately timed stages plus a complete path.

**Sweep:** Reuse count, state cardinality, update rate, partial groups and data distribution.

**Discriminating observation:** A measured break-even model that predicts held-out cases.

**Baseline:** Best direct representation including existing packed or vectorized alternatives.

**Confounders / correctness:** Omitting maintenance or final decoding creates fictional wins; scalar versus packed output contracts differ.

**Access gate:** Run CPU identity checks first; inspect sm70 lowering for packed intrinsics.

**Related:** C00 C01 C02 C07 C08 C09 C37.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e14"></a>


# E14 — Atomics as useful coordination

> How much semantic progress occurs per atomic transaction?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, atomics, as, useful, coordination.
**Prerequisites:** R12. **Evidence:** S03 S30.

**Question:** How much semantic progress occurs per atomic transaction?

**Minimal setup:** Benchmark reservation, merge and transition workloads with configurable target sharing and optional local aggregation.

**Sweep:** Contention, operation, width, returned-value dependence, distribution and failed CAS fraction.

**Discriminating observation:** Useful completed updates/second and latency tails, not merely raw issued attempts.

**Baseline:** Locally aggregated or phased alternatives at equal semantics.

**Confounders / correctness:** Atomicity does not publish other data. Hot lines and fairness can dominate.

**Access gate:** Supported operation and scope on the actual allocation; no race-based shortcut.

**Related:** C04 C24 C25 M29.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e15"></a>


# E15 — Publication and progress litmus

> Can the proposed bounded protocol violate payload or scheduling invariants?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, publication, and, progress, litmus.
**Prerequisites:** R12. **Evidence:** S17 S25 S30 S33.

**Question:** Can the proposed bounded protocol violate payload or scheduling invariants?

**Minimal setup:** First write a memory-model/progress proof. Then run finite epoch-tagged producer/consumer tests with protected termination and adversarial delays.

**Sweep:** Grid admission, stream ordering, queue fullness, counter wrap bounds and device/host placement.

**Discriminating observation:** Any stale payload, reused slot or blocked producer falsifies the implementation; no observed failures do not prove legality.

**Baseline:** A supported explicit phase/event protocol.

**Confounders / correctness:** Undefined races cannot be legalized by stress testing. A watchdog cannot substitute for a schedulable stop path.

**Access gate:** No unbounded spin test; use valid memory types, scopes and ordering.

**Related:** R06 C22 C24 C25.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e16"></a>


# E16 — Persistent roles and residency

> When does retained state repay queueing and reserved resources?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, persistent, roles, and, residency.
**Prerequisites:** R12. **Evidence:** S01 S30.

**Question:** When does retained state repay queueing and reserved resources?

**Minimal setup:** Compare bounded resident executors, batched kernels and graphs with the same task stream. Make producer progress explicit.

**Sweep:** Task size, skew, role split, register/shared footprint, occupancy and stop/drain behavior.

**Discriminating observation:** End-to-end throughput/tails and state-reuse benefit without starvation.

**Baseline:** Properly batched and graph-replayed conventional execution.

**Confounders / correctness:** Assuming all blocks are concurrently resident or treating smid as launch affinity invalidates the design.

**Access gate:** Supported cooperative admission where used; otherwise no global spin barrier.

**Related:** C19 C25 C34 M15.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e17"></a>


# E17 — DMA and compute overlap

> Which actors and routes make progress concurrently on this machine?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, dma, and, compute, overlap.
**Prerequisites:** R12. **Evidence:** S15 S30 S32.

**Question:** Which actors and routes make progress concurrently on this machine?

**Minimal setup:** Time each copy path and compute workload alone, serially and concurrently with explicit legal buffer lifetimes.

**Sweep:** Size, direction, buffer depth, local/peer/host routes and compute memory intensity.

**Discriminating observation:** A contention/overlap matrix including owner HBM and critical-path effects.

**Baseline:** SM copy/transform and public asynchronous copy paths.

**Confounders / correctness:** Asynchronous return is not physical overlap; roots, copy-engine assignment and power may be shared.

**Access gate:** No reset or clock changes; pinned allocation and actual engine capabilities recorded.

**Related:** C19 C23 C26 M36 R14.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e18"></a>


# E18 — Peer loads, cache behavior and latency

> What actually services repeated peer accesses on the tested path?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, peer, loads, cache, behavior, and, latency.
**Prerequisites:** R12. **Evidence:** S02 S25 S30.

**Question:** What actually services repeated peer accesses on the tested path?

**Minimal setup:** Use pointer chains and independent requests to peer allocations; compare read-only phases and correctly synchronized writes.

**Sweep:** Working set, stride, cache form, concurrency, allocation and owner-side traffic.

**Discriminating observation:** Signatures that separate startup, translation, caching and owner-memory contention.

**Baseline:** Local HBM and explicit peer staging.

**Confounders / correctness:** A latency reduction does not by itself prove requester L2 caching or coherent writable aliases.

**Access gate:** Validate peer capability and use legal ordering; no unsynchronized cache-coherence tests.

**Related:** R07 C20 M34.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e19"></a>


# E19 — Peer signaling and clock relationships

> How much does a complete GPU-to-GPU handshake cost?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, peer, signaling, and, clock, relationships.
**Prerequisites:** R12. **Evidence:** S03 S25 S30.

**Question:** How much does a complete GPU-to-GPU handshake cost?

**Minimal setup:** Use a finite epoch protocol with local send/receive intervals and separately estimate clock offset/drift through exchanges.

**Sweep:** Atomic versus event/command paths, polling cadence, message batch size and owner load.

**Discriminating observation:** Round-trip and tail latency plus explicit uncertainty for clock alignment.

**Baseline:** CUDA-visible event and staged communication protocols.

**Confounders / correctness:** Do not subtract raw timestamps from unsynchronized GPUs. Polling consumes fabric/cache service.

**Access gate:** Native peer operation support and a valid publication/progress proof.

**Related:** C20 C21 C22 M35 M47.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e20"></a>


# E20 — Actual NVLink routing and saturation

> Which links carry the traffic, and where does it saturate?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, actual, nvlink, routing, and, saturation.
**Prerequisites:** R12. **Evidence:** S02 S36 S26.

**Question:** Which links carry the traffic, and where does it saturate?

**Minimal setup:** Inventory link connectivity and run directed pair transfers with available link/PCIe telemetry.

**Sweep:** One-way, two-way, multiple streams, all pair combinations and concurrent owner compute.

**Discriminating observation:** Measured directional bandwidth and interference tied to the actual topology.

**Baseline:** Each isolated direct pair and supported alternative staging path.

**Confounders / correctness:** Bidirectional aggregates cannot be compared with one-way payload rates; counters may include protocol traffic.

**Access gate:** No assumed multi-hop forwarding or six-links-per-pair topology.

**Related:** R07 C23 M22.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e21"></a>


# E21 — Host NUMA ingress

> Can locality remove cross-socket traffic or supply independent host paths?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, host, numa, ingress.
**Prerequisites:** R12. **Evidence:** S30 S33 S36.

**Question:** Can locality remove cross-socket traffic or supply independent host paths?

**Minimal setup:** Place and verify host pages on each NUMA node, register/pin them, then transfer to each GPU with controlled producer affinity.

**Sweep:** Local/remote pages, individual/simultaneous directions and mapped versus staged access.

**Discriminating observation:** Latency/bandwidth differences explained by page placement and root topology.

**Baseline:** Conventional pinned transfers with verified local placement.

**Confounders / correctness:** Pinning and thread affinity do not prove page locality; existing data may originate remotely.

**Access gate:** Read-only topology inspection and supported OS allocation/registration.

**Related:** C23 M43 M44.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e22"></a>


# E22 — Stream memory operations

> Which wait/write semantics are reachable and useful on the installed stack?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, stream, memory, operations.
**Prerequisites:** R12. **Evidence:** S17 S42.

**Question:** Which wait/write semantics are reachable and useful on the installed stack?

**Minimal setup:** Query capabilities; test finite value handshakes with explicit CUDA-visible ordering and non-managed supported memory.

**Sweep:** 32/64-bit width, comparison mode, batch size, remote flush support and wrap bounds.

**Discriminating observation:** Correct completion and measured full pipeline cost versus shader/event alternatives.

**Baseline:** Events and a tiny bounded polling/update kernel.

**Confounders / correctness:** Memory dependencies can be invisible to CUDA scheduling. GEQ wrap semantics are not ordinary unbounded integer comparison.

**Access gate:** S17/S42 restrictions must be satisfied before submission.

**Related:** C22 C27 M31.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e23"></a>


# E23 — VMM alias and view behavior

> Can a legal view remove address work without hidden coherence or translation cost?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, vmm, alias, and, view, behavior.
**Prerequisites:** R12. **Evidence:** S18 S31.

**Question:** Can a legal view remove address work without hidden coherence or translation cost?

**Minimal setup:** Query granularity and permissions; construct isolated views with synchronized phase changes and a verified reference.

**Sweep:** View size, alias count, page footprint, window length and access phase.

**Discriminating observation:** Correct output plus mapping amortization and translation cost.

**Baseline:** Two-segment ring windows and simple modulo.

**Confounders / correctness:** Mapping success is not a complete concurrent-alias visibility contract. Do not remap live accesses.

**Access gate:** Public VMM supported by actual device/driver; no PTE edits.

**Related:** C29 M40 R08.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e24"></a>


# E24 — Fault and access-counter policy

> Is coarse remote-access feedback useful before the phase ends?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, fault, and, access-counter, policy.
**Prerequisites:** R12. **Evidence:** S16 S28 S29 S31.

**Question:** Is coarse remote-access feedback useful before the phase ends?

**Minimal setup:** Observe supported managed-memory advice/prefetch/migration behavior and available notifications under controlled locality phases.

**Sweep:** Phase duration, reuse, working set, advice and owner placement.

**Discriminating observation:** Policy lag, migration traffic and total time, not just fault counts.

**Baseline:** Explicit placement and fixed managed policies.

**Confounders / correctness:** Notifications may be driver-owned; shared-source defaults are not fixed hardware configuration. Avoid intentional overflow.

**Access gate:** No direct ATS/PTE changes without a separately established platform/driver contract.

**Related:** C30 C32 M41 M42.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e25"></a>


# E25 — Feedback cost and regret

> Does adaptation outperform a fixed policy after paying for observation and switching?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, feedback, cost, and, regret.
**Prerequisites:** R12. **Evidence:** S34 S35 S36.

**Question:** Does adaptation outperform a fixed policy after paying for observation and switching?

**Minimal setup:** Use a small set of already-correct kernels and repeat workloads with known phase changes. Log policy decisions.

**Sweep:** Observation frequency, hysteresis, noise, remaining horizon and switch/repacking cost.

**Discriminating observation:** Total regret versus best fixed and offline phase-aware controls.

**Baseline:** Fixed policies and a cheap density/time heuristic.

**Confounders / correctness:** Profiler replay and thermal drift can change the workload being controlled.

**Access gate:** Only installed compatible observation APIs; keep an uninstrumented control.

**Related:** C32 C33 M46.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e26"></a>


# E26 — Texture and SFU approximation

> Can a specialized arithmetic path meet a useful error/performance contract?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, texture, and, sfu, approximation.
**Prerequisites:** R12. **Evidence:** S30 S03.

**Question:** Can a specialized arithmetic path meet a useful error/performance contract?

**Minimal setup:** Compare table/interpolation, SFU seed/refinement and polynomial implementations over a bounded domain.

**Sweep:** Table spacing, formats, coordinate boundaries, derivative extremes and exceptional values.

**Discriminating observation:** Worst-case error and complete execution cost at equal accepted tolerance.

**Baseline:** Conventional function implementation and cached table/manual interpolation.

**Confounders / correctness:** Ideal interpolation error omits hardware coordinate/filter/sample precision. Random tests miss extrema.

**Access gate:** Documented Tesla CUDA texture/SFU path only; no assumed inaccessible graphics engine.

**Related:** C31 M10 M23.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e27"></a>


# E27 — Copy remap reachability

> Can the declared component transformer be safely invoked and outperform SM formatting?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, copy, remap, reachability.
**Prerequisites:** R12. **Evidence:** S12 S15.

**Question:** Can the declared component transformer be safely invoked and outperform SM formatting?

**Minimal setup:** Before any command, establish an owned driver/channel implementation and exact descriptor rules. Begin with tiny fixed records and a CPU reference.

**Sweep:** Expressible component selections, constants, widths, pitches and transfer sizes.

**Discriminating observation:** Correct transformation and full cost versus public copy plus/fused shader transform.

**Baseline:** Public memcpy and optimized SM conversion.

**Confounders / correctness:** Header fields do not provide complete ownership/format/lifetime semantics. No arbitrary gather assumed.

**Access gate:** K-level, NOT executable from the package; requires separate privileged engineering and recovery plan.

**Related:** C26 M37 R09.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e28"></a>


# E28 — Copy-engine semaphore actor

> Can completion-word operations replace a shader boundary in a real pipeline?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, copy-engine, semaphore, actor.
**Prerequisites:** R12. **Evidence:** S12 S15 S17.

**Question:** Can completion-word operations replace a shader boundary in a real pipeline?

**Minimal setup:** Establish a valid command route from pinned HAL evidence. Test release, increment and timestamp separately on isolated owned control storage.

**Sweep:** Counter values, INC/DEC threshold/wrap rules, flush modes and command sequencing.

**Discriminating observation:** Exact word semantics and complete pipeline latency without payload transfer.

**Baseline:** Public stream memory operations, events and tiny kernels.

**Confounders / correctness:** Reduction is on a semaphore word, not array data. Clocks and visibility domains must not be conflated.

**Access gate:** K-level until a safe public equivalent is used; no live CUDA-owned pushbuffer patching.

**Related:** C27 M38.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e29"></a>


# E29 — Dependent QMD minimal experiment

> Is there a usable restricted descriptor dependency beyond public graph execution?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, dependent, qmd, minimal, experiment.
**Prerequisites:** R12. **Evidence:** S27 S13 S40.

**Question:** Is there a usable restricted descriptor dependency beyond public graph execution?

**Minimal setup:** First resolve ownership, units, reference counts, cache visibility and completion from implementation evidence. Only then consider two finite known kernels.

**Sweep:** A single dependency/release relation before any circular or dynamic structure.

**Discriminating observation:** Correct bounded execution and total cost versus graph replay.

**Baseline:** Public instantiated graphs and batched launches.

**Confounders / correctness:** Descriptor fields alone do not prove arbitrary graph semantics or SM affinity. No self-modifying live descriptors.

**Access gate:** S/K frontier; no executable low-level command generator supplied.

**Related:** C28 M39 R09.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e30"></a>


# E30 — Binary transformation validation

> Does an edited cubin preserve semantics and improve the intended bottleneck?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, binary, transformation, validation.
**Prerequisites:** R12. **Evidence:** S04 S05 S11.

**Question:** Does an edited cubin preserve semantics and improve the intended bottleneck?

**Minimal setup:** Pin compiler/tool/architecture and hash original/edited binaries. Validate metadata, relocations, def/use and dependency controls before differential execution.

**Sweep:** Boundary inputs, resource pressure, memory latency and compiler baseline variants.

**Discriminating observation:** Exact or bounded outputs plus isolated and full-kernel performance evidence.

**Baseline:** Original ptxas output and source-level alternatives.

**Confounders / correctness:** A transformation can pass warm-cache tests yet fail under variable latency; random tests alone do not establish legality.

**Access gate:** B-level edits isolated to controlled experiments, not a claim of universal kernel rewriting.

**Related:** C17 C34 M48.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e31"></a>


# E31 — MPS and process interference

> What sharing, latency and failure boundaries hold on this exact Volta stack?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, mps, and, process, interference.
**Prerequisites:** R12. **Evidence:** S01 S41 S30.

**Question:** What sharing, latency and failure boundaries hold on this exact Volta stack?

**Minimal setup:** Use compatible documented MPS/IPC configurations and benign finite workloads in separate clients.

**Sweep:** Client count, resource fractions, work mix and isolated versus shared execution.

**Discriminating observation:** Per-client tails, aggregate useful work and observed interference.

**Baseline:** Separate conventional contexts and single-client runs.

**Confounders / correctness:** Current MPS docs may include unsupported newer variants; resource shares do not prove fairness or fatal-fault isolation.

**Access gate:** No deliberate fault injection on shared hardware; preserve process/resource lifetimes.

**Related:** M45 C25.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e32"></a>


# E32 — Launch, graphs and CDP

> Which supported submission mechanism best matches task granularity?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, launch, graphs, and, cdp.
**Prerequisites:** R12. **Evidence:** S30 S32 S06.

**Question:** Which supported submission mechanism best matches task granularity?

**Minimal setup:** Compare finite equivalent stages through host launches, instantiated graphs and supported device-side launch variants.

**Sweep:** Task size, repetition, parameter updates and dependency structure.

**Discriminating observation:** Host overhead, device idle gaps and total completion time.

**Baseline:** Properly batched launches with minimized unnecessary synchronization.

**Confounders / correctness:** Device-side launch is not a remote launch; modern graph/CDP features need exact target/version verification.

**Access gate:** Installed compatible APIs and per-device cooperative checks.

**Related:** M32 M33 C25 C28.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e33"></a>


# E33 — Power and steady-state behavior

> Is the proposed schedule faster after thermal and power transients settle?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, power, and, steady-state, behavior.
**Prerequisites:** R12. **Evidence:** S02 S36.

**Question:** Is the proposed schedule faster after thermal and power transients settle?

**Minimal setup:** Run equal-work schedules to stable conditions under unchanged supported limits; record clocks, temperature, power and useful outputs.

**Sweep:** Overlap ratio, phase order, neighbor activity and workload duration.

**Discriminating observation:** Sustained throughput and energy per result with raw telemetry context.

**Baseline:** Maximum-overlap and simple fixed schedules.

**Confounders / correctness:** Sensor averaging, ambient changes and reduced precision/work can manufacture apparent gains.

**Access gate:** No voltage/firmware modifications or unsafe power-limit changes.

**Related:** C33 M52.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e34"></a>


# E34 — RAS contamination audit

> Are performance or correctness observations confounded by hardware errors or recovery?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, ras, contamination, audit.
**Prerequisites:** R12. **Evidence:** S02 S28 S36.

**Question:** Are performance or correctness observations confounded by hardware errors or recovery?

**Minimal setup:** Read ECC, retired-page, link and management status before/after a normal finite benchmark.

**Sweep:** Normal repeated runs and existing health differences only.

**Discriminating observation:** Explicit exclusion/annotation of contaminated samples.

**Baseline:** Clean stable runs on the same device.

**Confounders / correctness:** Reset can involve NVLink peers; error absence in one log is not proof of perfect hardware.

**Access gate:** Read-only audit; no intentional ECC/link fault injection or routine resets.

**Related:** R13 M51.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e35"></a>


# E35 — Platform and electrical evidence

> Which module/baseboard details affect software-visible behavior?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, platform, and, electrical, evidence.
**Prerequisites:** R12. **Evidence:** S02 S36 S37 S39.

**Question:** Which module/baseboard details affect software-visible behavior?

**Minimal setup:** Collect exact SKU/part/VBIOS/BDF identifiers and available original platform documentation; inspect topology without physical modification.

**Sweep:** Device/OEM revisions, link widths, root placement and supported telemetry.

**Discriminating observation:** A source-backed platform matrix with explicit unresolved pins/rails/clock domains.

**Baseline:** Generic V100 assumptions, used only as hypotheses to check.

**Confounders / correctness:** SXM2 form factor does not prove identical wiring, firmware or enabled features.

**Access gate:** Read-only first; no probing unknown powered pins or firmware modifications.

**Related:** R13 R07 M49 M50.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e36"></a>


# E36 — Toolchain and library compatibility

> Which installed artifacts actually execute native sm70 paths?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, toolchain, and, library, compatibility.
**Prerequisites:** R12. **Evidence:** S06 S05 S32 S41.

**Question:** Which installed artifacts actually execute native sm70 paths?

**Minimal setup:** Compile a tiny native sm70 kernel with the intended toolchain; inspect cubin/fatbin and record driver/library build paths.

**Sweep:** Compiler versions, PTX/cubin selection and required library operators.

**Discriminating observation:** A per-feature compatibility matrix rather than a blanket CUDA-version claim.

**Baseline:** A preserved known-working sm70 toolchain and native binary.

**Confounders / correctness:** New driver API spelling does not imply a new hardware feature; management displayed version is not compiler version.

**Access gate:** No assumption that latest library releases retain Volta support.

**Related:** R10 M45 M48.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e37"></a>


# E37 — New PTX spelling on old silicon

> Does lop3.BoolOp expose useful sm70 code beyond the compiler baseline?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, new, ptx, spelling, on, old, silicon.
**Prerequisites:** R12. **Evidence:** S03 S05 S06.

**Question:** Does lop3.BoolOp expose useful sm70 code beyond the compiler baseline?

**Minimal setup:** Compile exact documented BoolOp syntax under a compatible PTX/ptxas version and inspect the native instruction and predicate path.

**Sweep:** Truth functions, predicate operation, live outputs and source expressions.

**Discriminating observation:** Correct truth tables plus any avoided result-test or predicate instruction.

**Baseline:** Clear CUDA Boolean expressions compiled for sm70.

**Confounders / correctness:** PTX 8.2 introduction is not a newer GPU requirement here, but installed compiler parsing still matters.

**Access gate:** Exact target notes and operand syntax checked before compilation.

**Related:** M01 R04 C00.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e38"></a>


# E38 — Negative-space falsification

> Which attractive interpretation is actually unsupported or algebraically wrong?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, negative-space, falsification.
**Prerequisites:** R12. **Evidence:** S03 S12 S27 S30.

**Question:** Which attractive interpretation is actually unsupported or algebraically wrong?

**Minimal setup:** Write the required primitive/contract, then check exact target/form, interface and algebra before any performance experiment.

**Sweep:** Claims such as partial-warp MMA, DMA array reduction, automatic peer coherence or generic semiring MMA.

**Discriminating observation:** A minimal contradiction or missing-contract statement attached to the rejected idea.

**Baseline:** A supported equivalent with explicit software work.

**Confounders / correctness:** Failure of one interface does not prove silicon impossibility; header presence does not prove usability.

**Access gate:** No malformed opcode/command execution merely to see whether it crashes.

**Related:** R00 R04 R09 C39.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

<a id="e39"></a>


# E39 — Complete composition usefulness

> Does the new representation improve the actual problem after all costs?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, complete, composition, usefulness.
**Prerequisites:** R12. **Evidence:** original synthesis; see linked mechanisms.

**Question:** Does the new representation improve the actual problem after all costs?

**Minimal setup:** Implement equal semantic workloads for a strong conventional, representation-changing and alternate-resource candidate.

**Sweep:** Shape, sparsity, distribution, reuse, accuracy and topology, including held-out cases.

**Discriminating observation:** End-to-end time/tails, memory use, energy and validity with a explainable crossover.

**Baseline:** Best applicable existing algorithm, not a straw-man scalar implementation.

**Confounders / correctness:** Preprocessing, maintenance, decoding, synchronization and output contracts must be included.

**Access gate:** All relevant correctness/capability tests passed; retain negative results.

**Related:** C39 R11 R15.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


---

# Source capsules


<a id="s01"></a>


# S01 — NVIDIA Volta Tuning Guide

**Version:** retrieved13.4, 2026-10-03

**Locator:** §1.4.1–1.4.6

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/volta-tuning-guide/index.html

Four static warp-scheduler sets per SM;64 FP32,32 FP64,64 INT32,8 tensor units. Core FMA dependence latency4 cycles. Limits:64 warps,64 K 32-bit registers,255 registers/thread,32 CTAs,96 KB shared per SM. Combined shared/L1/texture128 KB. Independent-thread scheduling needs explicit synchronization. MPS supports separate VAs but not fatal-fault isolation. INT/FP overlap does not imply all resource peaks add.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s02"></a>


# S02 — NVIDIA Tesla V100 architecture whitepaper

**Version:** WP-08608-001_v1.1, August2017

**Locator:** SM, memory, NVLink, module/platform sections

**Evidence type:** primary

**Source:** https://images.nvidia.com/content/volta-architecture/pdf/volta-architecture-whitepaper.pdf

Distinguish full GV100 die from enabled V100 SKU. Four HBM2 stacks; original nominal 900 GB/s. Six NVLink2 ports,25 GB/s each direction per port. Original SXM2 module140×78 mm and 300 W nominal. POWER9 coherence/ATS is platform-specific. Access counters and copy-engine address-fault support expose additional control machinery. HBM uses sideband ECC.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s03"></a>


# S03 — PTX ISA

**Version:** PTX 9.4 retrieved2026-10-03; exact target notes required

**Locator:** lop3; prmt; fns; match/shfl/vote; mma.m8n8k4; memory model; special registers

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/parallel-thread-execution/index.html

PTX is virtual ISA, not latency contract. sm70 half-input m8n8k4 performs four independent 8×8×4 products under a full-warp collective contract. Explicit fragments differ from opaque WMMA. lop3.BoolOp arrived in PTX 8.2 while supporting sm70. Cache operators are not synchronization. Exact operand forms and target notes govern availability.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s04"></a>


# S04 — Dissecting NVIDIA Volta via Microbenchmarking

**Version:** Jia et al.,2018

**Locator:** register banking; table 4.1; instruction caches; TLBs

**Evidence type:** primary

**Source:** https://arxiv.org/pdf/1804.06826

Historical empirical results identify two 64-bit register banks selected by register parity; some three-source same-bank32-bit operations conflict unless reuse changes reads. Reported dependent la ten cie s include common FP32/logic 4, IMAD 5, packed-half 6, FP64 arithmetic 8, POPC 10, FLO/BREV/MUFU 14 cycles. Cache/TLB observations depend on allocation, code and measurement regime.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s05"></a>


# S05 — CUDA Binary Utilities

**Version:** CUDA 12.9.1

**Locator:** Volta opcode table; nvdisasm; cuobjdump

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-binary-utilities/index.html

Machine code exposes convergence, operand and scheduling information absent from CUDA. The Volta mnemonic table includes IMMA, but names are not a validated operand-form capability matrix; do not override later-target restrictions in documented integer MMA forms.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s06"></a>


# S06 — Navigating GPU Architecture Support

**Version:** NVIDIA,4 August2025

**Locator:** offline targets and driver support

**Evidence type:** primary

**Source:** https://developer.nvidia.com/blog/navigating-gpu-architecture-support-a-guide-for-nvidia-cuda-developers/

CUDA 13 removes offline compilation below compute capability7.5. CUDA 12.9 retains sm70. R580 is the final driver branch for the older architectures with stated LTS through mid2028. Current individual library binaries require separate verification.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s07"></a>


# S07 — SparkAttention

**Version:** arXiv2502.12784 v1,2025

**Locator:** Volta fragment/accumulator discussion

**Evidence type:** primary

**Source:** https://arxiv.org/html/2502.12784v1

Volta-specific attention illustrates fragment-aware computation and the trade between FP16-accumulator conversion and FP32-fragment shuffle costs. Narrower storage is not automatically the cheaper complete pipeline.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s08"></a>


# S08 — CUDA Integer Intrinsics

**Version:** CUDA 12.9.1

**Locator:** __fns;__dp4a;__dp2a;__byte_perm; shifts; popcount

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__INT.html

Integer APIs include packed dots, set-bit search, permutation, multiply-high and funnel shifts. __fns has a base/offset contract and 0xffffffff no-result sentinel. CUDA byte_perm does not expose every PTX prmt selector behavior. Intrinsic names do not guarantee one SASS instruction.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s09"></a>


# S09 — CUDA SIMD Intrinsics

**Version:** CUDA 12.9.1

**Locator:** packed arithmetic/comparison/saturation

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__SIMD.html

Packed byte/halfword operations expose useful semantics, but sm70 instruction expansion must be inspected. Saturating, ordinary packed and scalar arithmetic are not interchangeable.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s10"></a>


# S10 — Using CUDA Warp-Level Primitives

**Version:** NVIDIA2018

**Locator:** membership masks; matching; synchronization

**Evidence type:** primary

**Source:** https://developer.nvidia.com/blog/using-cuda-warp-level-primitives/

Derive logical participants before divergence; incidental activemask is not a replacement. Match groups equal keys. Shuffle/vote do not provide a general memory fence. Producer lanes must participate and hold defined data.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s11"></a>


# S11 — CuAssembler

**Version:** upstream accessed2026-10-03; commit not captured

**Locator:** supported architectures; binary editing workflow

**Evidence type:** original tool

**Source:** https://github.com/cloudcores/CuAssembler

Original community assembler/reassembler tooling supports machine-code experiments. It is not a vendor guarantee of arbitrary transformation safety. Pin architecture/tool/compiler/cubin hashes before use.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s12"></a>


# S12 — VOLTA_DMA_COPY_A class C3B5

**Version:** official moving master accessed2026-10-03

**Locator:** REMAP_COMPONENTS; LAUNCH_DMA; semaphore; render enable

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/open-gpu-doc/master/classes/dma-copy/clc3b5.h

Command definitions expose component selection, constants, write suppression, pitch/block-linear addressing, conditional execution and completion reductions. Reductions concern a semaphore word, not every transferred array element. Header presence does not establish a public CUDA route.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s13"></a>


# S13 — VOLTA_COMPUTE_A class C3C0

**Version:** official moving master accessed2026-10-03

**Locator:** cache/launch/control methods

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/open-gpu-doc/master/classes/compute/clc3c0.h

Compute methods reveal cache, shader-window and launch-related controls beneath CUDA. Ownership and command semantics must be established before manipulation; field names are not full operational contracts.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s14"></a>


# S14 — NVIDIA open GPU kernel modules

**Version:** README accessed2026-10-03

**Locator:** supported hardware

**Evidence type:** primary

**Source:** https://github.com/NVIDIA/open-gpu-kernel-modules

Open kernel modules support Turing and newer, not V100. Released shared UVM/HAL source nevertheless includes useful Volta implementations. Source visibility must not be confused with a supported open driver for GV100.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s15"></a>


# S15 — Volta UVM copy-engine implementation

**Version:** R580.95.05

**Locator:** semaphore_release; reduction_inc; timestamp; memcopy; memset

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/580.95.05/kernel-open/nvidia-uvm/uvm_volta_ce.c

Pinned driver code emits release, increment and timestamp semaphore commands with data transfer disabled. It also demonstrates constant remapping for fill and explicit flush/pipelining choices. This is real control work outside SM kernels, not a general vector ALU or automatically callable user API.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s16"></a>


# S16 — Volta UVM MMU implementation

**Version:** R580.95.05

**Locator:** PTE apertures; NO_ATS; page levels

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/580.95.05/kernel-open/nvidia-uvm/uvm_volta_mmu.c

Code distinguishes video/coherent-system/peer apertures and 47-bit physical addressing. In ATS systems, NO_ATS directory policy spans 512 MB virtual regions to prevent CPU translation from defeating intended GPU faults. This is platform-specific, not an ordinary CUDA PTE-editing interface.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s17"></a>


# S17 — CUDA stream memory operations

**Version:** CUDA 12.9.1

**Locator:** WaitValue/WriteValue/BatchMemOp warnings

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-driver-api/group__CUDA__MEMOP.html

Stream memory waits/writes have capability and address restrictions; managed pointers are excluded. Dependencies created only by these operations are invisible to CUDA scheduling, so CUDA-visible ordering may also be required to prevent deadlock. Remote flush is conditional.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s18"></a>


# S18 — Low-level GPU VMM introduction

**Version:** NVIDIA, CUDA 10.2 introduction

**Locator:** reserve/create/map/setaccess

**Evidence type:** primary

**Source:** https://developer.nvidia.com/blog/introducing-low-level-gpu-virtual-memory-management/

Virtual reservation, backing and permissions can be controlled separately. Composite mappings do not merge execution domains or make remote memory uniform.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s19"></a>


# S19 — Accelerating Reduction and Scan Using Tensor Core Units

**Version:** Dakkak et al.,2018/ICS2019

**Locator:** reduction and prefix constructions

**Evidence type:** original research

**Source:** https://arxiv.org/pdf/1811.09736

Original work maps reductions/scans to matrix operations. Benefits depend on shape, batching and staging; this does not establish that a tensor construction beats an isolated shuffle scan.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s20"></a>


# S20 — FTTN: Feature-Targeted Numerical Testing

**Version:** Li et al.,2024

**Locator:** numerical feature tests; V100 results

**Evidence type:** original empirical research

**Source:** https://arxiv.org/html/2403.00232v1

Targeted tests report V100 truncation-related accumulation behavior and other format features that differ from a freely reordered chain of scalar IEEE FMAs. Validate exponent gaps, cancellation, subnormals and conversion separately; random-only agreement is insufficient.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s21"></a>


# S21 — Tensor Core Programmability, Performance and Precision

**Version:** Markidis et al.,2018

**Locator:** mixed precision accuracy recovery

**Evidence type:** original research

**Source:** https://arxiv.org/abs/1803.04014

Precision expansion uses additional products and conversion/conditioning work; it is an algorithm, not a native full-FP32 tensor mode.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s22"></a>


# S22 — CUTLASS sm70 MMA implementation

**Version:** CUTLASSv2.11.0

**Locator:** 8×8×4 inline PTX forms

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/cutlass/v2.11.0/include/cutlass/arch/mma_sm70.h

Explicit Volta MMA specializations expose row/column and accumulator forms. A logical group size of 8 does not remove the warp-wide instruction participation requirement.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s23"></a>


# S23 — CUTLASS Volta multiplicand layouts

**Version:** CUTLASSv2.11.0

**Locator:** congruous/crosswise layout classes

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/cutlass/v2.11.0/include/cutlass/layout/tensor_op_multiplicand_sm70.h

Volta-specific layouts use structured index permutations. Producer/consumer layout agreement can be more valuable than repeatedly materializing canonical arrays.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s24"></a>


# S24 — tcFFT

**Version:** Li et al.,2021

**Locator:** fragment manipulation and V100 evaluation

**Evidence type:** original research

**Source:** https://arxiv.org/pdf/2104.11471

Tensor-core FFT research demonstrates transform appropriation with fragment-aware data arrangements. Numerical format, size and benchmark conditions limit the result; it is not universal full-precision FFT replacement.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s25"></a>


# S25 — Using NVSHMEM

**Version:** retrieved2026-10-03; version-sensitive

**Locator:** symmetric addresses; CUDA model; transport prerequisites

**Evidence type:** primary

**Source:** https://docs.nvidia.com/nvshmem/api/latest/using.html

A symmetric pointer is local to its PE; remote addressing includes translation. GPU-side puts/gets/signals have explicit ordering and transport contracts. GPU-originated NIC communication has requirements beyond simply owning NVLink.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s26"></a>


# S26 — NCCL LL128 implementation

**Version:** NCCLv2.18.6-1

**Locator:** payload/flag movement and waits

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/nccl/v2.18.6-1/src/collectives/device/prims_ll128.h

Warp-cooperative payload and progress handling form a complete protocol. Borrowing polling or volatile operations without its ordering, channel and target assumptions is not a correctness argument.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s27"></a>


# S27 — Volta QMD v02_02

**Version:** official moving master accessed2026-10-03

**Locator:** dependent QMD; queues; release reductions; resource fields

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/open-gpu-doc/master/classes/compute/clc3c0qmd.h

Descriptor definitions include dependent scheduling, circular queues, release slots and resource/cache controls. They do not by themselves prove arbitrary dataflow execution, CUDA SM affinity or safe self-modifying command queues.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s28"></a>


# S28 — Volta UVM fault buffer

**Version:** R580.95.05

**Locator:** overflow and GET handling

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/580.95.05/kernel-open/nvidia-uvm/uvm_volta_fault_buffer.c

A concrete implementation comment requires advancing GET before clearing overflow because a same-cycle arriving fault can reassert it. Control queues have timing/ordering contracts; overflow is not an application scheduling primitive.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s29"></a>


# S29 — UVM access counters

**Version:** R580.95.05

**Locator:** batching; thresholds; migration policy

**Evidence type:** primary

**Source:** https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/580.95.05/kernel-open/nvidia-uvm/uvm_gpu_access_counters.c

Notifications are batched and interpreted by software policy. Shared multi-generation defaults are not a complete fixed V100 hardware specification or a free user-readable counter stream.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s30"></a>


# S30 — CUDA C++ Programming Guide

**Version:** CUDA 12.9.1

**Locator:** memory model; texture; cooperative launch; CDP; feature tables

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-c-programming-guide/index.html

Participation, ordering and progress are separate requirements. Streams need not run concurrently. Legacy atomics are not general acquire/release fences. Later cp.async, ldmatrix, mbarrier, clusters, TMA, DPX, TF32/BF16 tensor modes and L2-persistence controls must not be imported into ordinary sm70 designs.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s31"></a>


# S31 — CUDA VMM Driver API

**Version:** CUDA 12.9.1

**Locator:** allocation granularity; map; setaccess; unmap

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-driver-api/group__CUDA__VA.html

Capabilities/granularity and allocation handles/mappings/permissions are distinct. Remapping must obey lifetime and synchronization contracts. Alias accessibility is not a promise of coherent concurrent use through every view.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s32"></a>


# S32 — CUDA Device API

**Version:** CUDA 12.9.1

**Locator:** device and capability queries

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-driver-api/group__CUDA__DEVICE.html

Query the actual device/driver instead of inferring every capability from V100 branding. Capacity, cooperative support, managed/VMM and stream memory capabilities can have separate restrictions.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s33"></a>


# S33 — GPUDirect RDMA

**Version:** CUDA 12.9.1

**Locator:** BAR; registration; IOMMU; memory ordering

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/gpudirect-rdma/index.html

External DMA requires registration, lifetime and ordering discipline. BAR size and root topology matter. A kernel polling external writes is not automatically a correctly ordered shared-memory protocol.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s34"></a>


# S34 — CUPTI usage

**Version:** retrieved2026-10-03

**Locator:** activities; callbacks; profiling; sampling

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cupti/main/main.html

Tracing, sampling and counter collection differ in compatibility and overhead. Replay and callbacks can perturb a workload. Current API descriptions do not establish that a feature works on an R580 Volta stack.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s35"></a>


# S35 — Nsight Compute Profiling Guide

**Version:** retrieved2026-10-03

**Locator:** replay; cache/clock control; overhead

**Evidence type:** primary

**Source:** https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html

Profiling can replay work or change cache/clock conditions. Keep uninstrumented application timing separate from diagnostic counter runs.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s36"></a>


# S36 — nvidia-smi / management documentation

**Version:** retrieved2026-10-03

**Locator:** topology; UUID; NVLink; power; reset

**Evidence type:** primary

**Source:** https://docs.nvidia.com/deploy/nvidia-smi/index.html

UUID/BDF is more stable than ordinal identity. Capture topology, clocks, ECC and link state. Reset of older NVLink-connected devices may require a peer group; never treat reset as harmless microbenchmark setup.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s37"></a>


# S37 — Nouveau GV100 graphics

**Version:** Linuxv6.12

**Locator:** GV100 implementation

**Evidence type:** original implementation

**Source:** https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/gpu/drm/nouveau/nvkm/engine/gr/gv100.c

Firmware-backed graphics/context initialization is visible, but Tesla API availability is SKU-specific.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s38"></a>


# S38 — Nouveau GV100 MMU

**Version:** Linuxv6.12

**Locator:** GV100 implementation

**Evidence type:** original implementation

**Source:** https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/gpu/drm/nouveau/nvkm/subdev/mmu/gv100.c

Common and generation-specific MMU implementations compose; a small wrapper is not a complete translation specification.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s39"></a>


# S39 — Nouveau GV100 authenticated code region

**Version:** Linuxv6.12

**Locator:** GV100 implementation

**Evidence type:** original implementation

**Source:** https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/gpu/drm/nouveau/nvkm/subdev/acr/gv100.c

Authenticated firmware bootstrap reveals security/ownership boundaries, not arbitrary user programmability.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s40"></a>


# S40 — Nouveau GV100 FIFO

**Version:** Linuxv6.12

**Locator:** GV100 implementation

**Evidence type:** original implementation

**Source:** https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/gpu/drm/nouveau/nvkm/engine/fifo/gv100.c

Channels, runlists, preemption and engine faults sit below streams; their contract is required for safe command work.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s41"></a>


# S41 — NVIDIA MPS documentation

**Version:** retrieved2026-10-03; current/legacy split

**Locator:** MPS variants and compatibility

**Evidence type:** primary

**Source:** https://docs.nvidia.com/deploy/mps/latest/index.html

Current documentation includes newer MPS interfaces. Do not assume those controls are available on a Volta/R580 installation; use Volta-specific evidence and installed-version checks.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




<a id="s42"></a>


# S42 — CUDA Driver API types

**Version:** CUDA 12.9.1

**Locator:** device attributes; P2P attributes; stream wait flags

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-driver-api/group__CUDA__TYPES.html

Capabilities distinguish VMM, host page tables, cooperative launch,64-bit stream operations and remote-write flush. Some aliases are deprecated. Stream GEQ uses cyclic signed-difference comparison and needs bounded counter distance.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.




---


# Corrections and quarantined inferences

1. Full GV100 die resources are not identical to an enabled V100 SKU. Inventory the actual machine.
2. Six NVLink ports per GPU do not mean six ports to one peer. Bidirectional aggregate and one-way payload are different metrics.
3. VMM/UVA naming does not merge SM scheduling, cache coherence or physical latency.
4. Four m8n8k4 subproducts remain a full-warp collective. Eight logical participants do not authorize partial-warp execution.
5. Explicit PTX fragment maps do not license opaque WMMA layout assumptions.
6. Copy-engine semaphore reduction is not array reduction. A command field is not a public CUDA function.
7. Dependent QMD fields do not establish a programmable arbitrary task graph or ordinary CUDA SM affinity.
8. New PTX syntax can target old silicon. Conversely, a Volta-family mnemonic list can include forms not established on GV100/sm70. Integer WMMA sm72+ is not sm70 support.
9. Current NVIDIA open kernel modules do not support V100, despite useful Volta UVM source being published.
10. Complementary pipelines share issue, registers, memory and power; their peak throughputs cannot simply be added.
11. FP32 tensor accumulation is not a promise of arbitrary scalar IEEE FMA order. Numerical encodings need targeted validation and bounds.
12. SM/warp IDs are not automatically stable application identities. Cross-device timers are not assumed synchronized.
13. Independent-thread scheduling does not prove arbitrary spin-loop fairness or producer residency.
14. Pinning pages and pinning a host thread do not establish NUMA page locality. Removing an extra CPU copy does not remove PCIe DMA.
15. Cache hints and volatile do not repair publication races. Reservation does not mean payload completion.
16. A successful mapping/driver query does not establish remote cache policy or achieved bandwidth.
17. Public graph replay is a baseline for exotic command scheduling, not an abstraction to reject on philosophical grounds.
18. CPU algebra checks do not validate GPU code generation, hardware arithmetic rounding, ordering or speed.


---


# Open questions and confidence boundaries

These are deliberately unresolved premises, not silently assumed capabilities. A candidate may avoid one rather than solve it. No missing timing is represented as zero.

## U01 — Actual SKU, enabled resources and module firmware

No user machine was inventoried. Read R01; tests E00 E35.

## U02 — Complete SXM2 connector/strap/VRM schematic

A module outline is not an electrical design package. Read R13; tests E35.

## U03 — All clock-domain and power couplings

Exact PLL/link-clock relationships remain unestablished. Read R13; tests E33 E35.

## U04 — NVLink packet, credit and arbitration detail

Public bandwidth facts do not reconstruct the full protocol. Read R07; tests E20.

## U05 — Link striping and route selection per address

Do not infer six links to every peer or universal address hashing. Read R07; tests E20.

## U06 — Requester/owner cache policy for each peer path

Exact allocation/instruction/cache behavior requires targeted proof and measurement. Read R07; tests E18.

## U07 — All peer atomic operation/scope combinations

Capability and semantics depend on pair, allocation and operation. Read R06; tests E00 E19.

## U08 — Physical HBM/L2 address hash

One VA buffer cannot establish a universal physical map. Read R03; tests E07 E08.

## U09 — Queue, scoreboard and outstanding-request capacities

Historical throughput does not uniquely identify every hidden queue. Read R02; tests E02 E03.

## U10 — Current exact instruction and cache timings

Historical results are priors, not local measurements. Read R02; tests E02 E07.

## U11 — Undocumented raw IMMA behavior on GV100

Family mnemonic lists do not establish supported sm70 integer tensor forms. Read R04; tests E36 E38.

## U12 — General copy-remap application reachability

Fields and UVM fill code are not a full public API. Read R09; tests E27.

## U13 — Safe copy-engine control-word application route

Observed HAL operations still need a supported or validated owned channel. Read R09; tests E28.

## U14 — Complete dependent-QMD execution contract

Units, lifetimes, reference counts, cancellation and ordering are incomplete. Read R09; tests E29.

## U15 — Meaning and reachability of QMD scheduling masks

No direct CUDA SM-affinity interpretation is established. Read R09; tests E29.

## U16 — Actual VMM alias/cache behavior on the target stack

Mapping success alone does not prove intended concurrent alias semantics. Read R08; tests E23.

## U17 — Host roots, page placement and IOMMU configuration

Slot placement and prior recollection do not establish the current DMA path. Read R07; tests E00 E21.

## U18 — ATS applicability on the user platform

POWER9-specific evidence does not establish an x86 path. Read R08; tests E24 E35.

## U19 — Cheap application access-counter exposure

Some useful data is driver-owned or delayed. Read R12; tests E24 E25.

## U20 — Inter-GPU clock alignment

No synchronized timer guarantee is assumed. Read R12; tests E19.

## U21 — Complete tensor numerical model

Published targeted tests are valuable but not a proof for every input/form. Read R15; tests E10.

## U22 — Performance of the 40 original compositions

No local V100 benchmark was run. Read R11; tests E39.

## U23 — Persistent progress under actual competing workloads

Residency and fairness assumptions require a design proof and controlled tests. Read R06; tests E15 E16.

## U24 — Installed MPS/cooperative/graph variants

Current documentation may describe newer unsupported modes. Read R10; tests E31 E32 E36.

## U25 — Every current framework/library sm70 binary path

Each required operator/build needs inspection. Read R10; tests E36.

## U26 — Firmware ABI, authentication and programmable capacity

Embedded controllers are not assumed freely programmable. Read R13; tests E35.

## U27 — Tesla graphics/media engine accessibility

Shared ancestry or source classes are insufficient. Read R13; tests E26 E35 E38.

## U28 — Exhaustive silicon/compiler errata

Known evidence is not an all-revision errata catalogue. Read R13; tests E30 E35 E36.

## U29 — Independent engine/reset granularity

Recovery can affect peers and contexts. Read R13; tests E34.

## U30 — Patent-to-GV100 implementation mapping

Patents remain leads unless tied to concrete implementation. Read R00; tests E35 E38.

## U31 — Exhaustive GPU aggregation/virtualization literature

Retained comparative backlog, not a design choice or a completed survey. Read R00; tests E38.

## U32 — Other multi-die products as exact comparisons

Product packaging is not a substitute for verified semantics. Read R00; tests E38.

## U33 — Physical copy-engine assignment and routing

API async-engine counts do not fully map every transfer path. Read R09; tests E17.

## U34 — Cache/TLB geometry under every configuration

Allocation, code and platform can alter empirical interpretation. Read R03; tests E07 E08.

## U35 — Universal safe SASS transformation

No general arbitrary-kernel rewriting proof is claimed. Read R10; tests E30.

## U36 — Command-engine compositions versus public graphs

A deeper layer may have no useful performance advantage. Read R09; tests E28 E29 E32.


---


# Research scope ledger

All141 numbered domains0–140 from the expanded plan are retained. Ten additions make the algebra, interface and retrieval questions explicit. “Mapped” means addressed in synthesis, not exhaustively established in silicon or locally benchmarked. Open-frontier domains retain unresolved questions below.

|ID|Domain|Read|Status|
|---|---|---|---|
|P000|Methodology|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P001|Hardware identity|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P002|SXM2 module|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P003|SM anatomy|R02 R04 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P004|Warp scheduler|R02 R04 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P005|Instruction latency and pipelines|R02 R04 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P006|Register file|R02 R04 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P007|Register movement|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P008|Shuffle|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P009|Vote and masks|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P010|Predicates|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P011|Branches and reconvergence|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P012|Integer execution|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P013|LOP3|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P014|PRMT|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P015|Bit slicing|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P016|Packed subwords|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P017|SFU|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P018|Conversion|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P019|Tensor primitive|R05 R15 M24 M25 M26 M27 M28|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P020|General tensor algebra|R05 R15 M24 M25 M26 M27 M28|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P021|Tensor reinterpretation|R05 R15 M24 M25 M26 M27 M28|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P022|Fragments|R05 R15 M24 M25 M26 M27 M28|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P023|Mixed precision|R05 R15 M24 M25 M26 M27 M28|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P024|Shared memory|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P025|Bank-aware layout|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P026|Barriers|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P027|L1|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P028|L2|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P029|HBM2|R03 R08|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P030|Coalescing|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P031|Memory forms|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P032|Constant memory|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P033|Texture|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P034|Spilling|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P035|GMMU|R03 R08|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P036|TLB|R03 R08|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P037|UVA|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P038|VMM|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P039|Managed memory|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P040|Atomics|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P041|Atomic computation|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P042|Memory ordering|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P043|Persistent kernels|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P044|GPU scheduler|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P045|Dynamic parallelism|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P046|Cooperative groups|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P047|Historical multi-device cooperation|R06 R02 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P048|Special registers|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P049|Observations as data|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P050|Copy engines|R09 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P051|DMA actors|R09 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P052|SM versus DMA movement|R09 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P053|NVLink physical|R07 R08|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P054|NVLink endpoints|R07 R08|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P055|NVLink semantics|R07 R08|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P056|Remote load/store fabric|R07 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P057|Remote data structures|R07 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P058|Remote atomics|R07 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P059|NVLink synchronization|R07 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P060|Striping and routing|R07 R08|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P061|NVLink versus PCIe|R07 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P062|NVSwitch evidence|R07 R08|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P063|POWER9|R07 R08|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P064|PCIe endpoint|R07 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P065|BAR/MMIO|R07 R08|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P066|NUMA|R07 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P067|Host memory tier|R07 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P068|Launch path|R09 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P069|Channels/pushbuffers|R09 R14|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P070|Streams|R09 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P071|Events/semaphores|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P072|Graphs|R09 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P073|Contexts|R10 M45 M48|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P074|MPS|R10 M45 M48|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P075|Preemption|R02 R04 R14|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P076|IPC|R10 M45 M48|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P077|GPUDirect|R07 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P078|NVSHMEM|R07 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P079|NCCL|R07 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P080|Cubin|R10 M45 M48|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P081|PTX versus SASS|R10 M45 M48|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P082|SASS control encoding|R02 R04 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P083|Manual scheduling|R02 R04 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P084|Compiler-avoided forms|R02 R04 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P085|Representation first|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P086|Location as semantics|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P087|Computation by routing|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P088|Representation collapse|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P089|Computation by side effects|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P090|Pipeline heterogeneity|R02 R04 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P091|Warp specialization|R02 R04 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P092|SM specialization|R02 R04 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P093|Message passing|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P094|State machines|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P095|Graph computation|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P096|Sequence routing|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P097|Sparse algebra|R04 R02 A01|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P098|Distributed-system hierarchy|R06 R02 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P099|Counters|R12 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P100|Counter feedback|R12 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P101|Profiling APIs|R12 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P102|Telemetry|R12 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P103|Boot|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P104|Embedded controllers|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P105|Firmware configuration|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P106|Reset|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P107|Kernel driver|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P108|Open-module support|R13 R07 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P109|Nouveau|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P110|Linux PCI P2P|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P111|DGX-1 V|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P112|DGX-2|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P113|AC922|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P114|RAS|R13 R07 R09|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P115|Errata|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P116|Historical CUDA features|R10 M45 M48|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P117|Academic microbenchmarks|R12 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P118|Patents|R13 R07 R09|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P119|SASS tools|R10 M45 M48|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P120|Community experiments|R12 R14|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P121|Negative-space research|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P122|Physical limits|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P123|Unexposed plausible capabilities|R00 A01 R14 C39|SYNTHESIS_WITH_EXPLICIT_OPEN_FRONTIER|
|P124|Owned-system timing inference|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P125|Concurrency matrix|R12 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P126|Conflict matrix|R12 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P127|Latency hierarchy|R02 R04 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P128|Granularity hierarchy|R03 R08|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P129|Scope hierarchy|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P130|Computational-need index|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P131|Composition graph|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P132|Constraint inversion|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P133|Microbenchmark programme|R12 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P134|Experimental discipline|R12 R14|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P135|Source hierarchy|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P136|Contradictions|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P137|Confidence|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P138|Report layers|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P139|Research passes|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P140|No meta-device design|R00 A01 R14 C39|MAPPED_TO_SYNTHESIS_NOT_GPU_VERIFIED|
|P141|Carry-safe positional integer algebra|C07 M09 E01|ADDED_SYNTHESIS|
|P142|Certified approximate decisions and refinement|C14 R15 E10|ADDED_SYNTHESIS|
|P143|Carry-save bitset multiplicity|C37 M01 E01|ADDED_SYNTHESIS|
|P144|Command-engine reduction scope versus array arithmetic|C27 M38 E28|ADDED_SYNTHESIS|
|P145|QMD ownership and dependency proof gates|C28 M39 E29|ADDED_SYNTHESIS|
|P146|Compiler syntax age versus target age|R04 E37|ADDED_SYNTHESIS|
|P147|Whole-composition break-even and rejection|R11 C39 E39|ADDED_SYNTHESIS|
|P148|Source reachability independent of evidence confidence|R00|ADDED_SYNTHESIS|
|P149|Model-readable conditional retrieval and ledger maintenance|A00 A01|ADDED_SYNTHESIS|
|P150|Adjacent multi-die/GPU products and aggregation literature|R00 R07|OPEN_COMPARATIVE_BACKLOG|


---


# Original71-domain plan: retention map

The later0–140 plan supersedes organization, not questions. These predecessor domains remain in scope. Comparative products, patents and aggregation literature are retained as a backlog rather than implied to have a complete survey. Actual hardware measurements await an inventoried machine.

1. Exact hardware identity — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
2. SXM2 electrical architecture — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
3. HBM subsystem — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
4. Cache hierarchy — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
5. Memory-management hardware — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
6. NVLink physical architecture — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
7. NVLink atomics and consistency — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
8. PCIe subsystem — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
9. Host NUMA — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
10. Copy engines — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
11. SM execution — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
12. Tensor cores — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
13. Integer/bitwise execution — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
14. Warp machinery — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
15. Shared memory — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
16. Register file — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
17. Special registers — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
18. Grid/CTA scheduling — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
19. Launch path — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
20. Streams/events — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
21. Graphs — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
22. Dynamic parallelism — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
23. GPU-initiated remote work — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
24. NCCL internals — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
25. NVSHMEM internals — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
26. GPUDirect — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
27. CUDA IPC — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
28. Contexts — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
29. Modules/code loading — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
30. PTX compilation — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
31. SASS research — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
32. Memory instructions — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
33. Coalescing/remote transactions — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
34. Prefetch — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
35. Remote latency hiding — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
36. Atomic communication — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
37. Fence/barrier combinations — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
38. Multi-device cooperation — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
39. Preemption/isolation — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
40. MPS — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
41. Firmware/controllers — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
42. Kernel-driver boundary — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
43. Nouveau — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
44. Linux PCI/IOMMU — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
45. POWER9 — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
46. DGX-1 V — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
47. DGX-2/NVSwitch — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
48. RAS — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
49. Counters — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
50. NVML/topology — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
51. Hidden topology — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
52. Academic microarchitecture — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
53. Patents — OPEN comparative/history source backlog; no meta-device design.
54. Unusual legal CUDA — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
55. Undocumented command mechanisms — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
56. Security/isolation boundaries — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
57. Latency hierarchy — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
58. Bandwidth hierarchy — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
59. Concurrency — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
60. Resource ownership — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
61. Synchronization boundaries — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
62. Address-space boundaries — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
63. Submission boundaries — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
64. Hardware impossibility — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
65. CUDA-hidden capabilities — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
66. Other multi-die/device precedents — OPEN comparative/history source backlog; no meta-device design.
67. Historical GPU virtualization — OPEN comparative/history source backlog; no meta-device design.
68. GPU aggregation literature — OPEN comparative/history source backlog; no meta-device design.
69. Current software ecosystem — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
70. Unknowns/microbenchmarks — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.
71. Actual-board topology — See ledger/SCOPE.md, the computational-need index and the linked reference chapters.


---


# Updating the atlas

## Stable IDs and append-only evidence

Keep IDs stable. Add a claim or hypothesis instead of silently replacing an incompatible premise. For a correction, record old/new IDs, reason, source version and affected compositions. A source document, a source claim, a local result and an original hypothesis are different objects.

Required event fields: event_id, date, type, objects, summary, evidence, verification. Useful types: SOURCE_ADDED, CLAIM_ADDED, CLAIM_SUPERSEDED, HYPOTHESIS_ADDED, EXPERIMENT_RUN, NEGATIVE_RESULT, OPEN_QUESTION_RESOLVED. Do not promote H to E because a CPU identity test passed.

## Adding a measurement

Use experiments/result.schema.json and retain raw samples. Record exact hardware/software/topology, binary hashes, operating conditions, correctness and limitations. Compare a strong baseline including encoding, maintenance, synchronization and decoding. Register confidence separately for the measured regime and any extrapolation.

## Updating retrieval

Update manifest summaries/tags/prerequisites and need-index routes. Keep one card small enough to read independently. Link common correctness/numerical material instead of repeating it. A source header should be an optional deep read unless a low-level dependency changes the implementation choice.

Run tools/validate_atlas.py and tools/semantic_checks.py after edits. The manifest stores word counts and SHA256 hashes; use tools/refresh_manifest.py after intentional content changes, then validate again. The full compendium is a derived artifact; never treat it as the sole editable authority.

## Recording failure

A negative result names the representation, shape, distribution, numerical contract and failed cost/semantic assumption. Keep its raw evidence and a route from the relevant mechanism. Do not generalize “this tile lost” into “this entire hardware mechanism is useless.”

This ledger is maintained by explicit future edits. Nothing here schedules autonomous monitoring, background research or hardware experiments.


---

# Local semantic validation


CPU status: PASS. Assertions: 31094. Test groups: 15.


These validate algebra, encoding and logical coordinate mappings, not actual tensor rounding, memory coherence, generated SASS or performance. GPU experiments remain unrun.
