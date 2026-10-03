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
