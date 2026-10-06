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
