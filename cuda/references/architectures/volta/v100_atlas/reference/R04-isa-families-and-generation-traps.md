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
