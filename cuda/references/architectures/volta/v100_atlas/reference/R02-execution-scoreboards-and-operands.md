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
