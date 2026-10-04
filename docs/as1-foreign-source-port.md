# AS1 foreign source verification and canonical plan no-op

This bounded kernel source change supports the Control broker through a startup
capability, `Service(..., project_source_verifier=callable | None)`. No amendment
request, context, caller role, or declaration can install that capability.
Without it, foreign prerequisites remain `source_prerequisite_unavailable`.
The port grants neither filesystem authority nor project mutation access.

The callable receives a copied source locator and returns these required fields:

```python
{
    "project": "exact-configured-project-id",
    "project_uuid": "canonical-native-project-uuid",
    "revision": 123,                 # exact native integer revision
    "repository": "exact-alias",
    "path": "relative/source.md",
    "content_sha256": "64-lowercase-hex-characters",
}
```

The requested project must equal the returned configured ID or UUID. Repository,
path and hash must match exactly; any requested UUID/revision must also match.
Invalid identities or unavailable brokers produce typed unavailability;
substituted locators or changed hashes/revisions produce typed staleness.
Preview and apply verify prerequisites within their native review transaction.
The review binds the exact returned revision and UUID, so revision drift between
preview and apply invalidates the proposal. Declarations save the configured ID
and exact UUID/revision. Orientation context reads recheck those saved sources.
Committed receipt replay preserves its original receipt and reports current
readiness; replay does not pretend its historical sources are currently fresh.

Canonical plan no-op detection validates and projects the native application
inside a rollback-only SQLite savepoint, comparing normalized native contents
rather than update timestamps, task version increments or generated row IDs.
Identical declarations return `status: noop` through native `Unchanged`; no
revision, event, projection, task version, gate, evidence, claim, handoff or
fragment history changes. Explicit empty declarations retain clearing meaning;
omitted task declarations preserve current fields/details. Brief preservation
is scoped to the exact run, lane and task. Meaningful changes still execute the
native guards and application. Read-only plan diff projects an ephemeral native
SQLite copy, without writing the source authority.

Qualification uses disposable actual native authorities with separately bound
fixture child processes. The child identifies the actual Skills source root;
it does not spoof or qualify the deployed runtime binding. The fixture child
removes inherited `PROJECT_CONTROL_RELEASE_MANIFEST` and
`PROJECT_CONTROL_RELEASE_DIGEST` deployment pins while preserving the parent
environment. Its native runtime guard binds the actual source root, and the
fixture verifies imported service, plan and amendment module paths and SHA256
against the files being qualified. The required gate is:

```sh
/home/tumlinson/project-control/.venv/bin/python -m pytest todo-orchestrator/tests/test_as1_foreign_source_port.py -q
```

Existing workflow plan snapshot, execution contract and semantic state/history
regressions are also run in a separately source-bound fixture environment.
The implementation changes no live database or migrations, and makes no claim
about the unmigrated deployed authority. Comparison cost scales with authority
contents/history; large-authority performance has not been benchmarked.
