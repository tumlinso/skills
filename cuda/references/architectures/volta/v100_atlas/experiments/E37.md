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
