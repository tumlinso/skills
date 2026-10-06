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
