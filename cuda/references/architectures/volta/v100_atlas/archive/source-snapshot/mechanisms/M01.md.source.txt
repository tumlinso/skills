# M01 — LOP3 as a bank of Boolean circuits

> Make each bit an independent logical instance, then synthesize its transition rule.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** Boolean, FSM, support, branch elimination.
**Prerequisites:** R04 R15. **Evidence:** S03 S05.

## Established substrate [A/D; reachability C/P/B]

LOP3 evaluates a three-input Boolean truth table independently across a word. The immediate selects one function shared by the bit positions. The newer BoolOp form can also produce a predicate from result-nonzero and an input predicate on sm70; compiler acceptance and actual lowering remain testable.

## Appropriation hypothesis

Represent cells, edges or finite-state instances as bits rather than scalar records. One gate then evaluates32 instances per lane. Fuse eligibility, exclusion and frontier masks directly. Full-adder sum and carry use LUTs0x96 and 0xE8; a mux uses0xCA under index4a+2 b+c. Shared subexpressions can make a whole state transition a small circuit.

## Cost and rejection boundary

Bits do not communicate without shifts/shuffles. A run-time-varying rule per bit cannot be supplied by one immediate LUT. Count live planes and conversion cost; explicit PTX may produce exactly the same code as clear Boolean source. Exhaustive8-case gate tests are cheap, but compound-network and boundary tests remain necessary.

## Next reads

Compositions: C00 C01 C06 C37. Experiments: E01 E37.
