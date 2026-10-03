# C30 — Translation-policy zoning on an ATS platform

> An address-space boundary can be an algorithmic placement boundary.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** ATS, VMM, POWER9, policy.
**Prerequisites:** M41 M42 R08. **Evidence:** S16 S28 S29.

## Construction [S; reachability K/F]


The Volta MMU implementation exposes NO_ATS policy at a512 MB directory-region scale. On a compatible ATS platform, investigate grouping allocations by desired translation/fault behavior so CPU translation does not defeat a GPU-managed policy.

Separate immutable remote data, migra table state and strict GPU-resident control. First establish which controls are actually exposed by the installed driver; ordinary CUDA cannot be assumed to edit these bits.


## Why it could work

The existing implementation shows that address-space placement can affect translation policy, not merely naming. Coarse allocation zones might avoid unintended behavior or reduce policy conflicts.

## Full cost and strongest baseline

Compare normal managed advice, prefetch and explicit placement. Large granularity wastes flexibility; fault/migration delay can dwarf kernel work. This idea is not transferable to an x86 host simply because it has V100NVLink.

## Falsifier / rejection condition

Reject without the required platform/interface, or when the policy problem can be solved more cheaply through supported placement controls.

**Experiment:** E24 E35. This composition has not been benchmarked on a V100 here.
