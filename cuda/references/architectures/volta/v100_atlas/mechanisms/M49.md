# M49 — Embedded processors and firmware frontier

> Study exposed operations before imagining spare programmable cores.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** firmware, Falcon, boot, reset.
**Prerequisites:** R13. **Evidence:** S02 S37 S39 S40.

## Established substrate [D/R; S appropriation; reachability K/F]

Original driver sources reveal parts of authenticated boot, context and channel machinery. Embedded controllers have privileged duties and firmware boundaries; existence does not prove arbitrary user execution.

## Appropriation hypothesis

An exposed supervisory function could handle coarse health/power policy. Boot/reset study helps separate silicon from firmware/driver policy. Preserve unusual possibilities as leads with specific missing contracts.

## Cost and rejection boundary

No arbitrary firmware patching or signature bypass is assumed. Reset can involve peers. Controller RAM/ISA/ABI unknowns are open questions, not extra compute capacity. Require a minimal legal invocation before estimating performance.

## Next reads

Compositions: C33 C39. Experiments: E35 E34.
