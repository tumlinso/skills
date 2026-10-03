# M03 — PRMT as a tiny register lookup

> A byte-permutation unit can act as a limited table-selection circuit.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** PRMT, lookup, packing, sequence.
**Prerequisites:** R04. **Evidence:** S03 S08.

## Established substrate [A; reachability C/P]

Byte permutation selects from source-register bytes. CUDA byte_perm and the fuller PTX prmt selector modes are not identical, especially sign-replication behavior. The instruction works on a small fixed source set, not arbitrary memory.

## Appropriation hypothesis

Hold an eight-entry categorical table in two words and select four entries with a packed selector. Compose a shuffle for coarse owner-lane selection with byte extraction for a larger warp-resident table. Small transition tables, quantization/codebook decoding and sequence normalization are natural candidates.

## Cost and rejection boundary

Updating the table costs register work. Dynamic indexing of local arrays can spill, so explicitly structured selection matters. Compare shared and constant lookup, especially when indexes are uniform. Endianness, selector high bits and inactive owner lanes require tests; multiple words per owner add another selection stage.

## Next reads

Compositions: C03 C35. Experiments: E01 E05 E13.
