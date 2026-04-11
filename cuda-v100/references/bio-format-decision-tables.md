# Format Decision Tables

## Master Layout Selection

| Hot phase | Preferred layout | Why |
|---|---|---|
| Row-wise QC / normalization | CSR | Rows are the natural work unit |
| Sparse x dense projection with row outputs | CSR | Row-local work and row sharding stay simple |
| Repeated feature stats | CSC | Feature access becomes contiguous |
| Transient construction or merge | COO | Simpler assembly path |
| Stable block structure | BSR | Only if blocks are real and useful |
| Row-binned regularized access | SELL | Only after row skew analysis |

## Transpose Or Not

Transpose once when:

- there are many feature-wise passes
- CSC reuse is high
- the transpose cost can be amortized

Do not transpose just because:

- the current kernel is awkward
- one small feature-wise phase exists
- the matrix will soon be projected to dense anyway

## Sparse Or Dense

Stay sparse when:

- the matrix is still huge and mostly zeros
- the hot path is indexing, filtering, row stats, or SpMM-like work
- dense expansion would inflate memory traffic badly

Go dense when:

- projection or aggregation shrinks the problem enough
- downstream work is GEMM-heavy
- dense libraries will dominate total runtime after conversion

## Anti-Patterns

- CSR for repeated feature-heavy passes
- dense conversion before the sparse phase has actually collapsed
- COO as a long-lived steady-state format
- forcing BSR or SELL without structural evidence
