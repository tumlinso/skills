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
