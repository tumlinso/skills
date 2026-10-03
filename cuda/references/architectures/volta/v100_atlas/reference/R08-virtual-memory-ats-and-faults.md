# R08 — Virtual memory, ATS and faults

> Separate naming, backing, permission, residency and coherence before exploiting address-space structure.

**Status:** source-backed synthesis. **Depth:** 3.
**Read when:** VMM, UVA, ATS, TLB, managed memory.
**Prerequisites:** none. **Evidence:** S16 S18 S28 S29 S31 S38.


For any pointer ask five questions: who can name it, what physically backs it, which access permissions exist, where its page resides, and which visibility/order rules apply. UVA, peer mapping, managed memory and explicit V MM answer different subsets. None creates one kernel scheduler across GPUs.

VMM can make physical regions look contiguous, but the pages can have different owners/costs. Aliases suggest wraparound views and immutable repeated data; concurrent use must satisfy the actual mapping/cache contract. Remapping is a synchronized phase change, not presumed cheap per-element dispatch. Query capabilities and allocation granularity rather than infer them from header availability.

A concrete low-level clue appears in S16: different apertures and a47-bit physical-address implementation; ATS and GMMU paths interact. A NO_ATS directory policy spans 512 MB virtual regions so CPU translations do not defeat intended GPU faults. This motivates allocation zoning on an appropriate platform. It does not give ordinary CUDA permission to rewrite PTEs, nor make x86 automatically support the POWER9 path.

Fault replay and access notifications are finite asynchronous control systems. S28 records a real overflow-clear ordering race; S29 shows batched notification/migration policy. They can inform coarse placement adaptation, but faults are not a sensible assumed replacement for fine-grained branches. Notification delay and migration cost can exceed the useful phase length.

Representation questions: can a graph be ordered by page locality; can a view remove modulo/descriptor work without data motion; can ownership match migration granularity; can immutable views share backing legally? Each needs both a semantic proof and a cost test. VMM granularity and TLB page sizes must not be conflated. Alias success in one microbenchmark is not a universal coherence contract.
