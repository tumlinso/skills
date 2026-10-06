# S03 — PTX ISA

**Version:** PTX 9.4 retrieved2026-10-03; exact target notes required

**Locator:** lop3; prmt; fns; match/shfl/vote; mma.m8n8k4; memory model; special registers

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/parallel-thread-execution/index.html

PTX is virtual ISA, not latency contract. sm70 half-input m8n8k4 performs four independent 8×8×4 products under a full-warp collective contract. Explicit fragments differ from opaque WMMA. lop3.BoolOp arrived in PTX 8.2 while supporting sm70. Cache operators are not synchronization. Exact operand forms and target notes govern availability.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
