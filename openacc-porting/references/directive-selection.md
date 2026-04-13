# Directive Selection

Use this reference only after the region survives the portability review.

## `parallel loop`

Consider it when:

- the loop structure is already regular
- iteration independence is understood
- the mapping should stay explicit

Do not prefer it when:

- dependencies are still uncertain
- hidden helper behavior makes the loop semantics unclear

## `kernels`

Consider it when:

- a conservative first offload is useful
- the compiler can discover obvious parallel structure across a compact region
- you want a lower-commitment probe before tightening directives

Do not keep it by default when:

- the region needs precise control
- the compiler-generated structure becomes opaque or unstable

## `collapse`

Consider it when:

- nested loops are truly independent
- the extra parallelism matches the data layout

Do not use it just to increase parallelism count. If collapse destroys locality or complicates indexing, leave the nest structure alone.

## `reduction`

Consider it when:

- the accumulation variable is explicit
- the operation is associative enough for the required correctness contract

Do not hide a dependency problem behind a reduction clause. If the logic is really a scan or a staged dependency chain, classify it accordingly.

## `async`

Consider it when:

- data can stay resident
- there is meaningful overlap to exploit
- the dependency story is already stable

Do not add `async` during the first correctness pass. It adds value only when overlap is real and measurable.

## Selection Rule

Prefer the most boring directive set that keeps the first port correct. Micro-tuning comes later.
