# Standalone Skills paired AS1 release

`integrations/as1-paired-release.json` pins the immutable installed candidate,
standalone Project Control source commit, Skills source commit, worker digest,
and installation instructions. Its initial status is `pending`: candidate
identity checks do not establish actual qualification or deployment. Skills
contains neither a second Project Control checkout nor a Project Control gitlink.
The post-qualification receipt commit records the frozen runtime source pins;
it does not change the immutable candidate.

The controller retains native lifecycle and activation. Use the installed
candidate's launchers and release manifest together, with its `runtime-skills`
root. Do not redirect imports or copy Project Control source into Skills.
Installation must bind `PROJECT_CONTROL_RELEASE_MANIFEST` to the candidate's
`release-manifest.json`, `PROJECT_CONTROL_RELEASE_DIGEST` to its recorded SHA256,
and `PROJECT_CONTROL_SKILLS_ROOT` to the candidate's `runtime-skills`.
Registration and native profile discovery must be observed from actual live
clients, including the consolidated `project-control` registration and exact
observer/Codex/mutator surfaces. The standalone PC release consumer verifies
those bindings and instructions against raw installed and live observations.

Preserve the prior launcher and candidate. Execute and record the actual
`new -> old -> new` rollback with accepted queued jobs preserved, either using
a forward-compatible store or pausing dispatch while preserving the forward
store. Keep user projects, Todo revisions/history and NF1A unchanged; never
restore an old Todo database over committed work. The live proof must include
rollback, source-preserving adoption, unrelated work checks and raw artifact
hashes as required by `tests/as1/test_pc_as1_release.py` in standalone PC.

After actual Skills qualification and actual live release pass, bind their
external receipts. Supply the executed pytest case report, actual inference
receipt and root's actual live release receipt; these commands do not activate
anything or mutate Todo:

```sh
/home/tumlinson/project-control/.venv/bin/python integrations/as1_release.py \
  --bind-evidence \
  --skills-qualification /absolute/path/to/executed-skills-cases.json \
  --skills-real-proof /absolute/path/to/actual-sqa-q12/receipt.json \
  --live-release /home/tumlinson/.local/state/project-control/as1-bootstrap/release/live-receipt.json
/home/tumlinson/project-control/.venv/bin/python integrations/as1_release.py
/home/tumlinson/project-control/.venv/bin/python planning/adaptive-surface-v1/scripts/acceptance_gate.py --outcome SK-AS1-RELEASE
```

The binder checks hashes, exact source identity, all SQA cases, real inference
journeys and all standalone PC live release assertions before writing `passed`.
Missing, failed, stale or changed evidence fails. After binding, commit and push
the manifest before root records the native release gate and closes the task.
A change to the live validator requires recording its current digest and
reviewing it; changing the digest cannot substitute for a passing proof.
