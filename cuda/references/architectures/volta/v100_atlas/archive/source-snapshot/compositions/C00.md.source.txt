# C00 — Bit-sliced full adders and arbitrary local Boolean rules

> Use the scalar logic data path as many parallel one-bit circuits.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** Boolean, FSM, support, LOP3.
**Prerequisites:** M01 M06 R15. **Evidence:** S03 S05.

## Construction [H; reachability C/P]


Let a, b, c be bitplanes. With truth-table index 4 a+2 b+c, LOP3 immediate0x96 computes parity and 0xE8 computes majority:

```
s = a ^ b ^ c
carry = (a & b) | (a & c) | (b & c)
```

At every bit position, a+b+c=s+2·carry. A mux a?b: c has immediate0xCA. Compose these gates into counters, threshold logic or a finite-state transition. A word carries32 independent instances;32 lanes can therefore hold1024 such instances per plane. Neighbor dependence becomes explicit shifts or shuffles rather than scalar pointer traversal.


## Why it could work

The identity is exhaustive over eight input triples. There is no floating rounding or cross-bit carry because carry is kept as a separate plane. Shared subexpressions can let a transition reuse masks across multiple output planes. A rule derived once can remain compiled while state evolves many times.

## Full cost and strongest baseline

Compare compiler-generated Boolean code, not only hand-written PTX. Include encoding, neighbor exchange, plane storage and extraction. A one-step scalar workload may never repay bit slicing. A variable rule per bit needs additional selection and cannot use one common immediate for free.

## Falsifier / rejection condition

Reject when encoding/decoding dominates, when the circuit grows beyond useful register/code footprint, or when required cross-instance dependencies turn each step into expensive routing. Exhaustively test small rules and valid-lane boundaries.

**Experiment:** E01 E13 E37. This composition has not been benchmarked on a V100 here.
