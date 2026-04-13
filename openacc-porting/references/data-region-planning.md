# Data-Region Planning

Use this reference when the question is where data should live and how transfer boundaries will affect the port.

## Host And Device Ownership

For each candidate region, identify:

- read-only inputs
- outputs written once
- arrays updated over multiple iterations
- scratch or temporary buffers
- ownership that is obvious versus ambiguous

Prefer explicit ownership over inferred ownership. If aliasing or lifetime is unclear, record it as a blocker instead of guessing.

## Data-Region Rules

Prefer wider, stable data regions when:

- the same arrays participate in several kernels or loops
- repeated call boundaries would otherwise force transfers
- setup or teardown work is cheap relative to the steady-state loop

Prefer narrower regions when:

- the region is only a correctness probe
- data is touched once and never reused
- the surrounding code makes residency assumptions unsafe

## Transfer Smells

Treat these as warning signs:

- entering and exiting a data region around every tiny loop
- helper-function boundaries that copy or remap the same buffers repeatedly
- frequent allocation or reallocation of device-visible storage
- temporary buffers whose lifetime is shorter than the transfer cost they trigger
- hidden structure copies caused by wrappers or by-value interfaces

## Call-Boundary Risk

Function boundaries often force accidental transfers when:

- ownership is split across helpers with unclear mutation rules
- the hot loop calls small helpers that were never written with device residency in mind
- one side of the boundary assumes host pointers while the other assumes device-resident data

If a call boundary is the problem, prefer a small restructuring that keeps data resident over repeated enter or exit clauses.

## What A Good Plan Looks Like

A good data-region plan says:

- which buffers should enter once and stay resident
- which regions can share one outer data scope
- which helpers need signature or ownership cleanup
- which transfers are unavoidable and should remain explicit

Do not describe every clause. Describe the residency boundary and the reason it is worth keeping.
