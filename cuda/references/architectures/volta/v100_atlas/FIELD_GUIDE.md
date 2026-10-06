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
