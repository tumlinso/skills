# Native skill routing and normal handoff

Coder, mutator and scout read installed SKILL.md with filesystem/command access,
then follow authored maps, references, prerequisites and explicit cross-skill
links. No observer read/skill adapter or injected overview is required. Indexes,
including skill_context graphs, are navigation acceleration; they cannot override
the skill's routing semantics. An absent map falls back to the installed entry
and its documented references, with uncertainty reported rather than invented.

The observer skill agent is homed in the registered canonical Skills directory.
It reads the installed entry first and reasons about the applicable branches,
then proposes paths, full source hashes, ranges/anchors, selection reasons and
prerequisite relationships. Project Control validates access, rereads authority,
checks freshness, and owns durable jobs, packets and provenance. A stale source
requires refresh/reselection or explicit partial authority. Model synthesis is
separate from exact source excerpts. Catalog completeness includes inaccessible,
missing and unsupported registrations explicitly; a flat search result is not
an authoritative route. The final public skill adapter is a PC consumer surface
requirement, not proof that deployed legacy aliases have already disappeared.

When guidance materially informs work, include a compact `skill_use` payload
alongside the existing context publication/handoff/finish flow. Include `skill`,
installed `skill_sha256`, `status: applied`, task/run identity, route/topic,
`reason`, source-bound project path/subsystem `anchors`, and result/decision refs
when available. Existing task-scoped `publish_project_context` kernel support
is retained beneath Project Control; native actors use their authorized workflow
context path rather than directly mutating a migrated authority. A read by itself
is `consulted` and must not become an applied relevance declaration. Changed
source anchors invalidate current relevance while historical usage is retained.
A skill hash records the version actually used; changed installed guidance must
be refreshed or marked for review without erasing that history.

The routing catalog is `native-skill-catalog.json`. It describes the four
accessible standalone Skills entries and nested routes. It does not enumerate
arbitrary external Codex skills or advertise MANIFEST default coverage. Missing
external dependencies are explicit. CUDA and ctxpp technical corpus baseline
hashes are captured separately in the AS1 routing baseline; no technical body,
atlas IDs/edges, compendium, ZIP or unknown AppleDouble archive is rewritten.

Todo Orchestrator remains the canonical internal semantic/transactional kernel
beneath Project Control, not a second plan or operator front end. Standalone
Skills contains no second Project Control implementation. Source remains the
separate `/home/tumlinson/project-control` authority. Paired standalone release
manifests follow qualification; routing instructions are not a release receipt.
