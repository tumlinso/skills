# M41 — ATS and fault replay as coarse policy machinery

> Address translation can shape layout, but its useful controls are platform-specific.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** ATS, POWER9, MMU, faults.
**Prerequisites:** R08 R13. **Evidence:** S02 S16 S28 S38.

## Established substrate [D; reachability K/F; managed C]

Volta MMU source describes apertures and an ATS NO_ATS policy spanning 512 MB virtual regions. CPU translation can otherwise defeat an intended GPU fault. Replay uses finite hardware/software queues.

## Appropriation hypothesis

On an appropriate ATS platform, zone allocation classes by translation policy. Coarse fault/migration feedback can help placement. This is not an attempt to make every fine branch a page fault.

## Cost and rejection boundary

POWER9 features do not follow from x86 NVLink presence. Normal CUDA does not allow arbitrary PTE edits. Fault cost, lag and queue pressure can overwhelm benefits. Exact timing and user reachability remain unmeasured.

## Next reads

Compositions: C30. Experiments: E24 E35.
