"""SEM-01..03: execute the Skills semantic authority against disposable repos.

Run with /home/tumlinson/project-control/.venv/bin/python -m unittest discover
-s tests/as1 -p test_sk_as1_semantics.py. No installed Todo copy or live DB is used.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

SKILLS = Path(__file__).resolve().parents[2]
TODO = SKILLS / "todo-orchestrator"
sys.path.insert(0, str(TODO))
sys.path.insert(0, str(TODO / "tests"))

from v2_helpers import V2Repo, base_plan, safe_task
from todo_orchestrator.models import TodoError
from todo_orchestrator.db import MIGRATIONS
from todo_orchestrator.service import Service
from todo_orchestrator.workflow.context_fragments import ContextFragmentStore, FragmentOwner


class AS1SemanticAcceptance(unittest.TestCase):
    def setUp(self):
        self.assertEqual(Path(sys.modules[Service.__module__].__file__).resolve(),
                         TODO / "todo_orchestrator" / "service.py")
        self.repo = V2Repo()
        self.addCleanup(self.repo.close)
        self.service = self.repo.service
        (self.repo.root / "src/a").mkdir(parents=True)
        (self.repo.root / "src/a/contract.txt").write_text("source contract\n")

    def request(self, action, payload, *, operation_id="acceptance-operation-1", mode="apply"):
        return {"format": "pc-project-amendment/1", "project": self.service.project["project_uuid"],
                "action": action, "intent": "Exercise canonical AS1 behavior",
                "expected_revision": self.service.db.revision(), "operation_id": operation_id,
                "payload": payload, "mode": mode}

    def amend(self, request):
        return self.service.amend_project(request, role="mutator")

    def identity(self, identity="package-one", version="1"):
        return {"id": identity, "repository": str(self.repo.root), "version": version}

    def anchor(self, path="src/a/contract.txt"):
        return {"project": self.service.project["project_uuid"], "repository": str(self.repo.root),
                "path": path, "content_sha256": hashlib.sha256((self.repo.root / path).read_bytes()).hexdigest()}

    def skill(self, status="applied"):
        return {"id": "skill-route", "skill": "cuda/references/volta", "status": status,
                "reason": "Informed the owned contract", "anchors": [self.anchor()]}

    def rows(self, table):
        # The tables are fixed test constants; all assertions use a read connection.
        with self.service.db.read() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM " + table)]

    @pytest.mark.as1_case("SEM-01")
    def test_sem01_declarations_survive_restart_and_export_without_read_revision(self):
        before = self.service.db.revision()
        result = self.amend(self.request("register_identity", self.identity()))
        self.assertEqual(result["status"], "applied")
        self.assertEqual(self.service.db.revision(), before + 1)
        self.service = Service(self.repo.root, read_only=True)
        context = self.service.project_context()
        self.assertIn("package-one", json.dumps(context["declarations"]))
        exported = self.service.export()["state"]["semantic_context"]
        self.assertEqual(exported["declarations"], context["declarations"])
        self.assertEqual(self.service.db.revision(), before + 1)

    @pytest.mark.as1_case("SEM-01")
    def test_sem01_legacy_import_keeps_unknown_notes_and_orphaned_owner(self):
        fixture = TODO / "tests/fixtures/legacy"
        for name in ("todos.md", "todo-status.md"):
            shutil.copy2(fixture / name, self.repo.root / name)
        shutil.copytree(fixture / "todos", self.repo.root / "todos", dirs_exist_ok=True)
        imported = self.service.migrate_markdown(True)
        self.assertEqual(imported["tasks_imported"], 2)
        tasks = self.rows("tasks")
        alpha = next(row for row in tasks if row["id"] == "alpha")
        self.assertEqual(alpha["status"], "attention_required")
        self.assertEqual(alpha["legacy_owner"], "agent-old")
        self.assertIn("This unknown section must survive", alpha["legacy_payload_json"])
        self.amend(self.request("register_identity", self.identity()))
        self.assertEqual(self.rows("tasks"), tasks)
        self.assertIn("package-one", json.dumps(self.service.project_context()))

    @pytest.mark.as1_case("SEM-02")
    def test_sem02_preview_noop_and_replay_are_revision_preserving(self):
        request = self.request("register_identity", self.identity(), mode="preview")
        before = self.service.db.revision()
        preview = self.amend(request)
        self.assertEqual(preview["status"], "preview")
        self.assertEqual(self.service.db.revision(), before)
        request["mode"] = "apply"
        applied = self.amend(request)
        self.assertEqual(applied["status"], "applied")
        after = self.service.db.revision()
        events = self.rows("events")
        replay = self.amend(request)
        self.assertEqual(replay["status"], "replayed")
        self.assertEqual(replay["receipt"], applied["receipt"])
        noop = self.amend(self.request("register_identity", self.identity(),
                                       operation_id="acceptance-noop-1"))
        self.assertEqual(noop["status"], "noop")
        self.assertEqual(self.service.db.revision(), after)
        self.assertEqual(self.rows("events"), events)

    def test_sem02_changed_reviewed_record_is_refused_not_recomputed(self):
        self.amend(self.request("register_identity", self.identity()))
        reviewed = self.request("register_identity", self.identity(version="2"),
                                operation_id="reviewed-change-1", mode="preview")
        self.amend(reviewed)
        self.amend(self.request("register_identity", self.identity(version="3"),
                               operation_id="concurrent-change-1"))
        before = self.service.project_context()
        reviewed["mode"] = "apply"
        with self.assertRaises(TodoError):
            self.amend(reviewed)
        self.assertEqual(self.service.project_context(), before)

    def test_sem02_unrelated_edit_does_not_invalidate_declaration_review(self):
        reviewed = self.request("register_identity", self.identity(), mode="preview")
        self.amend(reviewed)
        (self.repo.root / "unrelated.txt").write_text("unrelated user work\n")
        self.amend(self.request("register_identity", self.identity("other-package"),
                               operation_id="unrelated-registration-1"))
        reviewed["mode"] = "apply"
        self.assertEqual(self.amend(reviewed)["status"], "applied")
        self.assertEqual((self.repo.root / "unrelated.txt").read_text(), "unrelated user work\n")

    def test_sem02_operation_id_cannot_rebind_to_different_payload(self):
        request = self.request("register_identity", self.identity())
        self.amend(request)
        before = self.service.project_context()
        changed = copy.deepcopy(request)
        changed["payload"]["version"] = "2"
        with self.assertRaises(TodoError):
            self.amend(changed)
        self.assertEqual(self.service.project_context(), before)

    @pytest.mark.as1_case("SEM-02")
    def test_sem02_successful_terminal_gate_proof_and_dirty_work_are_preserved(self):
        task = safe_task("A", "src/a", gates=[{"id": "CHECK", "type": "file_exists",
                         "path": "src/a/contract.txt", "input_paths": ["src/a/contract.txt"],
                         "required": True}])
        self.repo.apply(base_plan([task]))
        claim = self.service.continue_work(task_id="A")
        token = claim["claim"]["claim_token"]
        self.service.gate_run("CHECK", token)
        self.service.complete(token, "validated", "source-backed fixture proof")
        before = {table: self.rows(table) for table in
                  ("tasks", "gates", "evidence", "task_completion_gates", "handoffs")}
        (self.repo.root / "src/a/unfinished.txt").write_text("preserve unfinished user data\n")
        self.amend(self.request("register_identity", self.identity()))
        self.assertEqual({table: self.rows(table) for table in before}, before)
        self.assertEqual((self.repo.root / "src/a/unfinished.txt").read_text(),
                         "preserve unfinished user data\n")

    def test_sem01_snapshot_restores_semantics_and_idempotency_receipts(self):
        request = self.request("register_identity", self.identity())
        applied = self.amend(request)
        before = self.service.project_context()
        original_path = self.service.paths.db_file
        self.service.export()
        # Switch only this disposable repository's state location, retaining its
        # canonical snapshot and identity. Service performs the supported restore.
        os.environ["TODO_ORCHESTRATOR_STATE_DIR"] = str(self.repo.root / "restored-runtime")
        restored = Service(self.repo.root)
        self.assertNotEqual(restored.paths.db_file, original_path)
        self.assertTrue(original_path.exists())
        after_restore = restored.project_context()
        self.assertEqual({k: v for k, v in after_restore.items() if k != "project_revision"},
                         {k: v for k, v in before.items() if k != "project_revision"})
        self.assertEqual(after_restore["project_revision"], before["project_revision"] + 1)
        replay = restored.amend_project(request, role="mutator")
        self.assertEqual(replay["status"], "replayed")
        self.assertEqual(replay["receipt"], applied["receipt"])
        self.assertEqual(restored.db.revision(), after_restore["project_revision"])

    def test_sem01_additive_migration_keeps_legacy_core_readable_without_read_writes(self):
        legacy_migrations = {version: sql for version, sql in MIGRATIONS.items() if version <= 11}
        with patch.dict(MIGRATIONS, legacy_migrations, clear=True):
            legacy = V2Repo()
            self.addCleanup(legacy.close)
            legacy.apply(base_plan([safe_task("LEGACY", "src/legacy")]))
        old_service = legacy.service
        with old_service.db.read() as conn:
            old_hash = hashlib.sha256(conn.serialize()).hexdigest()
            old_tasks = [dict(row) for row in conn.execute("SELECT * FROM tasks")]
        old_revision = old_service.db.revision()
        reader = Service(legacy.root, read_only=True)
        self.assertIn("LEGACY", json.dumps(reader.status()))
        self.assertEqual(reader.export()["state"]["semantic_context"]["status"], "unavailable")
        with self.assertRaises(TodoError) as error:
            reader.project_context()
        self.assertEqual(error.exception.code, "schema_migration_required")
        with reader.db.read() as conn:
            self.assertEqual(hashlib.sha256(conn.serialize()).hexdigest(), old_hash)
        self.assertEqual(reader.db.revision(), old_revision)
        migrated = Service(legacy.root)
        with migrated.db.read() as conn:
            self.assertEqual([dict(row) for row in conn.execute("SELECT * FROM tasks")], old_tasks)
        self.assertEqual(migrated.db.revision(), old_revision)
        self.assertEqual(migrated.project_context()["declarations"], [])

    def test_sem03_observer_and_coder_cannot_promote_project_declarations(self):
        request = self.request("register_identity", self.identity())
        before = self.service.db.revision()
        for role in ("observer", "coder", "codex", "investigator"):
            with self.subTest(role=role), self.assertRaises(TodoError):
                self.service.amend_project(request, role=role)
        self.assertEqual(self.service.db.revision(), before)

    def test_sem03_untrusted_provider_cannot_grant_executable_or_access(self):
        before = self.service.db.revision()
        for payload in ({"id": "evil", "provider_id": "arbitrary-command", "options": {}},
                        {"id": "evil", "provider_id": "python", "options": {"command": "touch sentinel"}},
                        {"id": "evil", "provider_id": "python", "options": {"root": "/tmp"}}):
            with self.subTest(payload=payload), self.assertRaises(TodoError):
                self.amend(self.request("configure_provider", payload))
        self.assertEqual(self.service.db.revision(), before)
        self.assertFalse((self.repo.root / "sentinel").exists())

    def test_sem01_consulted_and_applied_skill_context_remain_distinct(self):
        self.amend(self.request("record_skill_use", self.skill("consulted")))
        first = self.service.project_context()["skill_uses"][0]
        self.assertEqual(first["payload"]["status"], "consulted")
        self.amend(self.request("record_skill_use", self.skill("applied"),
                               operation_id="applied-skill-use-1"))
        current = self.service.project_context()["skill_uses"][0]
        self.assertEqual(current["payload"]["status"], "applied")
        self.assertEqual(current["version"], first["version"] + 1)
        self.assertEqual(current["payload"]["anchors"], [self.anchor()])

    def test_sem03_trusted_provider_options_do_not_expand_host_trust(self):
        self.service.project["configuration"]["project_providers"] = {
            "python-imports": {"allowed_options": {"enabled": [True, False]}}}
        safe = {"id": "imports", "provider_id": "python-imports", "options": {"enabled": True}}
        self.assertEqual(self.amend(self.request("configure_provider", safe))["status"], "applied")
        before = self.service.db.revision()
        for added in ({"executable": "/bin/sh"}, {"options": {"command": "touch sentinel"}},
                      {"options": {"enabled": "true"}}, {"root": "/tmp"}):
            with self.subTest(added=added), self.assertRaises(TodoError):
                self.amend(self.request("configure_provider", {**safe, **added},
                                        operation_id="bad-provider-option-1"))
        self.assertEqual(self.service.db.revision(), before)

    @pytest.mark.as1_case("SEM-03")
    def test_sem03_scoped_coder_publication_cannot_promote_or_escape_claim(self):
        self.repo.apply(base_plan([safe_task("A", "src/a"), safe_task("B", "src/b")]))
        claim = self.service.continue_work(task_id="A")
        token = claim["claim"]["claim_token"]
        request = {"kind": "skill_use", "task_id": "A", "payload": self.skill()}
        published = self.service.publish_project_context(request, claim_token=token)
        self.assertEqual(published["status"], "published")
        use = self.service.project_context()["skill_uses"][0]
        self.assertEqual((use["task_id"], use["origin"]), ("A", "task_scoped"))
        before = self.service.db.revision()
        self.assertEqual(self.service.publish_project_context(request, claim_token=token)["status"], "noop")
        (self.repo.root / "src/b").mkdir()
        (self.repo.root / "src/b/outside.txt").write_text("other task data\n")
        outside = copy.deepcopy(request)
        outside["payload"]["anchors"] = [self.anchor("src/b/outside.txt")]
        for bad in ({**request, "task_id": "B"}, {**request, "kind": "identity"}, outside):
            with self.subTest(bad=bad), self.assertRaises(TodoError):
                self.service.publish_project_context(bad, claim_token=token)
        self.assertEqual(self.service.db.revision(), before)

    @pytest.mark.as1_case("SEM-03")
    def test_sem03_amendment_invalidates_related_fragment_and_preserves_unrelated(self):
        plan = base_plan([safe_task("A", "src/a")])
        plan["schema_version"] = 3
        plan["runs"] = [{"id": "RUN", "root_task_id": "A", "charter": {"objective": "bounded"},
                         "lanes": [{"id": "ROOT", "role": "coordinator", "tasks": []},
                                   {"id": "I", "parent_lane_id": "ROOT", "role": "integrator", "tasks": ["A"]}]}]
        self.repo.apply(plan)
        store = ContextFragmentStore(self.service.db)
        owner = FragmentOwner("RUN")
        related, _ = store.publish(actor_session_id=None, owner=owner, kind="decision_ledger",
                                   content={"declaration_id": "package-one"})
        unrelated, _ = store.publish(actor_session_id=None, owner=owner, kind="run_charter",
                                     content={"declaration_id": "other-package"})
        self.amend(self.request("register_identity", self.identity()))
        self.assertFalse(store.get(related.id).active)
        self.assertTrue(store.get(unrelated.id).active)
        invalidations = self.service.project_context()["invalidations"]
        self.assertEqual({row["kind"] for row in invalidations}, {"graph", "search", "orientation"})
        self.assertEqual({row["entity_id"] for row in invalidations}, {"package-one"})

    def test_sem02_retirement_preserves_foreign_relation_with_same_entity_id(self):
        self.amend(self.request("register_identity", self.identity()))
        local = {"project_uuid": self.service.project["project_uuid"], "repository": str(self.repo.root),
                 "kind": "identity", "id": "package-one"}
        foreign = {**local, "project_uuid": "foreign-project", "repository": "foreign-repository"}
        consumer = {**local, "kind": "module", "id": "consumer"}
        for identity, target in (("local-consumer", local), ("foreign-consumer", foreign)):
            self.amend(self.request("register_relation", {"id": identity, "source": consumer,
                                  "target": target, "relation": "uses"}, operation_id=identity + "-operation"))
        removed = self.amend(self.request("remove_registration", {"id": "package-one", "kind": "identity",
                                         "version": 1}, operation_id="remove-local-identity"))
        self.assertEqual(removed["status"], "applied")
        remaining = {row["id"] for row in self.service.project_context()["declarations"]}
        self.assertIn("foreign-consumer", remaining)
        self.assertNotIn("local-consumer", remaining)
        self.assertNotIn("package-one", remaining)

    def test_sem03_coder_alias_anchor_cannot_bypass_source_freshness(self):
        self.repo.apply(base_plan([safe_task("A", "src/a")]))
        token = self.service.continue_work(task_id="A")["claim"]["claim_token"]
        payload = self.skill()
        alias_anchor = {**self.anchor(), "project": self.service.project["project_name"],
                        "content_sha256": "0" * 64}
        payload["anchors"].append(alias_anchor)
        before = self.service.db.revision()
        with self.assertRaises(TodoError):
            self.service.publish_project_context({"kind": "skill_use", "payload": payload}, claim_token=token)
        self.assertEqual(self.service.db.revision(), before)
        self.assertEqual(self.service.project_context()["skill_uses"], [])

    def test_sem02_replay_returns_current_workflow_readiness(self):
        self.repo.apply(base_plan([safe_task("A", "src/a")]))
        request = self.request("register_identity", self.identity())
        applied = self.amend(request)
        initial = self.amend(request)
        self.assertEqual(initial["current_readiness"], self.service.ready()["tasks"])
        self.assertTrue(initial["current_readiness"])
        self.service.continue_work(task_id="A")
        before = self.service.db.revision()
        replay = self.amend(request)
        self.assertEqual(replay["receipt"], applied["receipt"])
        self.assertEqual(replay["current_readiness"], self.service.ready()["tasks"])
        self.assertFalse(replay["current_readiness"])
        self.assertEqual(replay["project_revision"], before)
        self.assertEqual(self.service.db.revision(), before)

    @pytest.mark.as1_case("SEM-01")
    def test_sem01_orientation_freshness_tracks_each_field_source_on_read(self):
        (self.repo.root / "src/a/map.txt").write_text("module map\n")
        payload = {"id": "project-purpose", "fields": {"purpose": "owned purpose", "map": "module map"},
                   "anchors": [self.anchor()],
                   "field_anchors": {"purpose": [self.anchor()], "map": [self.anchor("src/a/map.txt")]}}
        self.amend(self.request("update_orientation", payload))
        before = self.service.db.revision()
        row = self.service.project_context()["orientation"][0]
        self.assertEqual({key: value["status"] for key, value in row["field_freshness"].items()},
                         {"purpose": "fresh", "map": "fresh"})
        (self.repo.root / "src/a/contract.txt").write_text("changed purpose source\n")
        changed = self.service.project_context()["orientation"][0]
        self.assertEqual({key: value["status"] for key, value in changed["field_freshness"].items()},
                         {"purpose": "stale", "map": "fresh"})
        (self.repo.root / "unrelated.txt").write_text("unrelated source edit\n")
        self.assertEqual(self.service.project_context()["orientation"][0]["field_freshness"],
                         changed["field_freshness"])
        self.assertEqual(self.service.db.revision(), before)

    @pytest.mark.as1_case("SEM-03")
    def test_sem03_replacement_and_removal_invalidate_previous_source_path_fragments(self):
        plan = base_plan([safe_task("A", "src/a")])
        plan["schema_version"] = 3
        plan["runs"] = [{"id": "RUN", "root_task_id": "A", "charter": {"objective": "bounded"},
                         "lanes": [{"id": "ROOT", "role": "coordinator", "tasks": []},
                                   {"id": "I", "parent_lane_id": "ROOT", "role": "integrator", "tasks": ["A"]}]}]
        self.repo.apply(plan)
        (self.repo.root / "src/a/new.txt").write_text("new source\n")
        old = {"id": "source-map", "fields": {"purpose": "old source"}, "anchors": [self.anchor()]}
        self.amend(self.request("update_orientation", old))
        store = ContextFragmentStore(self.service.db)
        owner = FragmentOwner("RUN")
        related, _ = store.publish(actor_session_id=None, owner=owner, kind="decision_ledger",
                                   content={"source": "src/a/contract.txt"})
        unrelated, _ = store.publish(actor_session_id=None, owner=owner, kind="run_charter",
                                     content={"source": "unrelated/path.txt"})
        replacement = {**old, "fields": {"purpose": "new source"}, "anchors": [self.anchor("src/a/new.txt")]}
        self.amend(self.request("update_orientation", replacement, operation_id="replace-source-map"))
        self.assertFalse(store.get(related.id).active)
        self.assertTrue(store.get(unrelated.id).active)
        new_fragment, _ = store.publish(actor_session_id=None, owner=owner, kind="decision_ledger",
                                        content={"source": "src/a/new.txt"})
        self.amend(self.request("remove_registration", {"id": "source-map", "kind": "orientation", "version": 2},
                               operation_id="remove-source-map"))
        self.assertFalse(store.get(new_fragment.id).active)
        self.assertTrue(store.get(unrelated.id).active)
        self.assertEqual(self.service.project_context()["orientation"], [])

    @pytest.mark.as1_case("SEM-03")
    def test_sem03_local_project_anchor_cannot_substitute_foreign_repository(self):
        self.repo.apply(base_plan([safe_task("A", "src/a")]))
        token = self.service.continue_work(task_id="A")["claim"]["claim_token"]
        foreign = {**self.anchor(), "repository": "foreign-repository"}
        orientation = {"id": "foreign-map", "fields": {"purpose": "foreign source"}, "anchors": [foreign]}
        before = self.service.db.revision()
        with self.assertRaises(TodoError):
            self.amend(self.request("update_orientation", orientation))
        payload = {**self.skill(), "anchors": [foreign]}
        with self.assertRaises(TodoError):
            self.service.publish_project_context({"kind": "skill_use", "payload": payload}, claim_token=token)
        self.assertEqual(self.service.db.revision(), before)
        context = self.service.project_context()
        self.assertEqual(context["orientation"], [])
        self.assertEqual(context["skill_uses"], [])


if __name__ == "__main__":
    unittest.main()
