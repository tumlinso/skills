# Open questions and confidence boundaries

These are deliberately unresolved premises, not silently assumed capabilities. A candidate may avoid one rather than solve it. No missing timing is represented as zero.

## U01 — Actual SKU, enabled resources and module firmware

No user machine was inventoried. Read R01; tests E00 E35.

## U02 — Complete SXM2 connector/strap/VRM schematic

A module outline is not an electrical design package. Read R13; tests E35.

## U03 — All clock-domain and power couplings

Exact PLL/link-clock relationships remain unestablished. Read R13; tests E33 E35.

## U04 — NVLink packet, credit and arbitration detail

Public bandwidth facts do not reconstruct the full protocol. Read R07; tests E20.

## U05 — Link striping and route selection per address

Do not infer six links to every peer or universal address hashing. Read R07; tests E20.

## U06 — Requester/owner cache policy for each peer path

Exact allocation/instruction/cache behavior requires targeted proof and measurement. Read R07; tests E18.

## U07 — All peer atomic operation/scope combinations

Capability and semantics depend on pair, allocation and operation. Read R06; tests E00 E19.

## U08 — Physical HBM/L2 address hash

One VA buffer cannot establish a universal physical map. Read R03; tests E07 E08.

## U09 — Queue, scoreboard and outstanding-request capacities

Historical throughput does not uniquely identify every hidden queue. Read R02; tests E02 E03.

## U10 — Current exact instruction and cache timings

Historical results are priors, not local measurements. Read R02; tests E02 E07.

## U11 — Undocumented raw IMMA behavior on GV100

Family mnemonic lists do not establish supported sm70 integer tensor forms. Read R04; tests E36 E38.

## U12 — General copy-remap application reachability

Fields and UVM fill code are not a full public API. Read R09; tests E27.

## U13 — Safe copy-engine control-word application route

Observed HAL operations still need a supported or validated owned channel. Read R09; tests E28.

## U14 — Complete dependent-QMD execution contract

Units, lifetimes, reference counts, cancellation and ordering are incomplete. Read R09; tests E29.

## U15 — Meaning and reachability of QMD scheduling masks

No direct CUDA SM-affinity interpretation is established. Read R09; tests E29.

## U16 — Actual VMM alias/cache behavior on the target stack

Mapping success alone does not prove intended concurrent alias semantics. Read R08; tests E23.

## U17 — Host roots, page placement and IOMMU configuration

Slot placement and prior recollection do not establish the current DMA path. Read R07; tests E00 E21.

## U18 — ATS applicability on the user platform

POWER9-specific evidence does not establish an x86 path. Read R08; tests E24 E35.

## U19 — Cheap application access-counter exposure

Some useful data is driver-owned or delayed. Read R12; tests E24 E25.

## U20 — Inter-GPU clock alignment

No synchronized timer guarantee is assumed. Read R12; tests E19.

## U21 — Complete tensor numerical model

Published targeted tests are valuable but not a proof for every input/form. Read R15; tests E10.

## U22 — Performance of the 40 original compositions

No local V100 benchmark was run. Read R11; tests E39.

## U23 — Persistent progress under actual competing workloads

Residency and fairness assumptions require a design proof and controlled tests. Read R06; tests E15 E16.

## U24 — Installed MPS/cooperative/graph variants

Current documentation may describe newer unsupported modes. Read R10; tests E31 E32 E36.

## U25 — Every current framework/library sm70 binary path

Each required operator/build needs inspection. Read R10; tests E36.

## U26 — Firmware ABI, authentication and programmable capacity

Embedded controllers are not assumed freely programmable. Read R13; tests E35.

## U27 — Tesla graphics/media engine accessibility

Shared ancestry or source classes are insufficient. Read R13; tests E26 E35 E38.

## U28 — Exhaustive silicon/compiler errata

Known evidence is not an all-revision errata catalogue. Read R13; tests E30 E35 E36.

## U29 — Independent engine/reset granularity

Recovery can affect peers and contexts. Read R13; tests E34.

## U30 — Patent-to-GV100 implementation mapping

Patents remain leads unless tied to concrete implementation. Read R00; tests E35 E38.

## U31 — Exhaustive GPU aggregation/virtualization literature

Retained comparative backlog, not a design choice or a completed survey. Read R00; tests E38.

## U32 — Other multi-die products as exact comparisons

Product packaging is not a substitute for verified semantics. Read R00; tests E38.

## U33 — Physical copy-engine assignment and routing

API async-engine counts do not fully map every transfer path. Read R09; tests E17.

## U34 — Cache/TLB geometry under every configuration

Allocation, code and platform can alter empirical interpretation. Read R03; tests E07 E08.

## U35 — Universal safe SASS transformation

No general arbitrary-kernel rewriting proof is claimed. Read R10; tests E30.

## U36 — Command-engine compositions versus public graphs

A deeper layer may have no useful performance advantage. Read R09; tests E28 E29 E32.
