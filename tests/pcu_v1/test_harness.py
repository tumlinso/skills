from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "unification/pcu-v1/scripts/pcu_harness.py"
SCHEMA = ROOT / "unification/pcu-v1/contracts/release-manifest.schema.json"
MIGRATOR = ROOT / "unification/pcu-v1/fixtures/fixture_migrator.py"
SPEC = importlib.util.spec_from_file_location("pcu_harness", SCRIPT)
assert SPEC and SPEC.loader
HARNESS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HARNESS
SPEC.loader.exec_module(HARNESS)


def run(*argv: str, cwd: Path) -> str:
    result = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise AssertionError(f"command failed: {argv}\n{result.stderr}")
    return result.stdout.strip()


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    run("git", "init", "-q", "-b", "main", cwd=path)
    run("git", "config", "user.email", "fixture@example.invalid", cwd=path)
    run("git", "config", "user.name", "PCU Fixture", cwd=path)
    return path


def commit_all(repo: Path, message: str) -> str:
    run("git", "add", "--all", cwd=repo)
    run("git", "commit", "-q", "-m", message, cwd=repo)
    return run("git", "rev-parse", "HEAD", cwd=repo)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def release_manifest(parent: str, tree_digest: str) -> dict[str, object]:
    observer = [
        "project_overview", "project_delta", "project_frontier", "inspect", "evidence",
        "plan_preview", "agent_status", "performance_status", "architecture_context",
        "coordination_view", "source_context", "history_trace", "impact_preview",
        "program_context", "terminal_capture",
    ]
    codex = [
        "next_task", "inspect_task", "coordinate_task", "delegate_task",
        "collect_delegation", "finish_task", *observer[:-1],
    ]
    return {
        "schema_version": 1,
        "product_name": "project-control",
        "package_version": "1.0.0",
        "source_parent_commit": parent,
        "source_tree_hash": tree_digest,
        "project_control_tool_schema_version": 3,
        "observer_tool_names": observer,
        "observer_schema_hashes": {name: digest(name) for name in observer},
        "codex_tool_names": codex,
        "codex_schema_hashes": {name: digest(name) for name in codex},
        "todo_kernel_contract_hash": digest("kernel"),
        "profile_contract_hash": digest("profile"),
        "migration_contract_hash": digest("migration"),
        "installer_contract_hash": digest("installer"),
        "test_evidence_digest": digest("tests"),
        "supported_todo_schema_versions": [10],
        "supported_project_front_doors": ["project-control", "coding-workflow"],
        "compatibility_aliases": ["coding-workflow"],
        "created_at": "2026-08-30T00:00:00Z",
        "authority_to_install": False,
    }


class ReleaseHarnessTests(unittest.TestCase):
    def test_manifest_source_and_lock_validation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            repo = init_repo(temp / "project-control")
            (repo / "source.txt").write_text("candidate\n")
            parent = commit_all(repo, "candidate source")
            manifest = release_manifest(parent, HARNESS.git_tree_digest(repo, parent))
            manifest_path = repo / "PCU_RELEASE.json"
            manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
            release = commit_all(repo, "release manifest")
            loaded = HARNESS.validate_release_manifest(manifest_path, SCHEMA)
            self.assertEqual(HARNESS.validate_release_source(loaded, repo, release)["release_commit"], release)

            lock = {
                "schema_version": 1,
                "project_control_commit": release,
                "manifest_sha256": HARNESS.sha256_file(manifest_path),
                "source_tree_hash": manifest["source_tree_hash"],
                "remote_url": "https://example.invalid/project-control.git",
            }
            lock_path = temp / "PCU_RELEASE.lock.json"
            lock_path.write_text(json.dumps(lock))
            self.assertEqual(HARNESS.validate_release_lock(lock_path, manifest_path, repo), lock)

    def test_manifest_rejects_hash_name_skew(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            repo = init_repo(temp / "repo")
            (repo / "source").write_text("x")
            parent = commit_all(repo, "source")
            manifest = release_manifest(parent, HARNESS.git_tree_digest(repo, parent))
            del manifest["observer_schema_hashes"]["inspect"]
            path = temp / "manifest.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(HARNESS.HarnessError):
                HARNESS.validate_release_manifest(path, SCHEMA)


class CloneAndSubmoduleTests(unittest.TestCase):
    def test_recursive_fresh_clone_has_independent_common_dirs_and_exact_pin(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            child = init_repo(temp / "project-control-origin")
            (child / "pc.txt").write_text("release\n")
            pin = commit_all(child, "release")

            parent = init_repo(temp / "skills-origin")
            (parent / "skills.txt").write_text("skills\n")
            commit_all(parent, "skills")
            run("git", "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(child), "project-control", cwd=parent)
            modules = parent / ".gitmodules"
            modules.write_text(modules.read_text().replace(str(child), "https://example.invalid/project-control.git"))
            commit_all(parent, "pin project-control")
            self.assertEqual(HARNESS.verify_submodule_pin(parent, "project-control", pin)["commit"], pin)

            clone = HARNESS.clone_independent(
                parent,
                temp / "fresh-clone",
                recursive=True,
                git_config={f"url.{child}.insteadOf": "https://example.invalid/project-control.git"},
            )
            self.assertNotEqual(HARNESS.git_common_dir(parent), HARNESS.git_common_dir(clone))
            self.assertEqual(run("git", "-C", "project-control", "rev-parse", "HEAD", cwd=clone), pin)

    def test_clone_refuses_existing_or_nested_destination(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = init_repo(Path(raw) / "repo")
            (repo / "file").write_text("x")
            commit_all(repo, "one")
            with self.assertRaises(HARNESS.HarnessError):
                HARNESS.clone_independent(repo, repo / "nested")
            existing = Path(raw) / "existing"
            existing.mkdir()
            with self.assertRaises(HARNESS.HarnessError):
                HARNESS.clone_independent(repo, existing)


class CandidateAndRollbackTests(unittest.TestCase):
    def test_candidate_plan_is_deterministic_and_nonexecuting(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            skills = init_repo(temp / "skills")
            (skills / "todo-orchestrator").mkdir()
            (skills / "tracked").write_text("skills")
            commit_all(skills, "skills")
            project_control = init_repo(temp / "project-control")
            (project_control / "tracked").write_text("pc")
            commit_all(project_control, "pc")
            destination = temp / "candidate-venv"
            plan = HARNESS.candidate_plan(
                skills_root=skills,
                project_control_root=project_control,
                destination=destination,
                rollback_state=temp / "rollback.json",
            )
            self.assertFalse(destination.exists())
            self.assertEqual(plan, HARNESS.candidate_plan(
                skills_root=skills,
                project_control_root=project_control,
                destination=destination,
                rollback_state=temp / "rollback.json",
            ))
            self.assertIn(str(skills / "todo-orchestrator"), plan.commands[1])
            self.assertIn(str(project_control), plan.commands[1])

    def test_atomic_swap_runs_rollback_on_verification_failure(self) -> None:
        calls: list[str] = []

        def runner(argv, cwd):
            calls.append(argv[0])
            if argv[0] == "verify-fail":
                raise RuntimeError("fixture failure")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with self.assertRaisesRegex(HARNESS.HarnessError, "rollback attempted"):
            HARNESS.atomic_swap(
                forward_commands=[["install"]],
                verify_commands=[["verify-fail"]],
                rollback_commands=[["restore-registration"], ["restore-service"]],
                runner=runner,
            )
        self.assertEqual(calls, ["install", "verify-fail", "restore-registration", "restore-service"])


class MigrationRehearsalTests(unittest.TestCase):
    def test_dry_run_apply_reapply_remove_is_independent_and_reversible(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            source = init_repo(temp / "downstream-fixture")
            (source / ".todo-orchestrator").mkdir()
            (source / "AGENTS.md").write_text(
                "user content\n\n<!-- coding-workflow:start -->\nold fixture guidance\n<!-- coding-workflow:end -->\n"
            )
            project = {
                "configuration": {"workflow_front_door": "coding-workflow"},
                "project_uuid": "00000000-0000-4000-8000-000000000001",
            }
            (source / ".todo-orchestrator/project.json").write_text(json.dumps(project, sort_keys=True, indent=2) + "\n")
            (source / ".todo-orchestrator/state.sqlite3").write_bytes(b"fixture-authority")
            commit_all(source, "fixture downstream")
            python = sys.executable
            result = HARNESS.rehearse_migration(
                source=source,
                destination=temp / "rehearsal",
                dry_run_command=[python, str(MIGRATOR), "dry-run"],
                apply_command=[python, str(MIGRATOR), "apply"],
                remove_command=[python, str(MIGRATOR), "remove"],
                allowed_paths=["AGENTS.md", ".todo-orchestrator/project.json"],
                immutable_paths=[".todo-orchestrator/state.sqlite3"],
                immutable_json_fields={".todo-orchestrator/project.json": ["project_uuid"]},
            )
            self.assertTrue(result.source_unchanged)
            self.assertTrue(result.independent_common_dir)
            self.assertEqual(result.apply_changed_paths, (".todo-orchestrator/project.json", "AGENTS.md"))
            self.assertTrue(result.reapply_idempotent)
            self.assertTrue(result.remove_restored)
            self.assertTrue(result.original_ancestry_reachable)

    def test_rehearsal_rejects_mutation_outside_owned_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            source = init_repo(temp / "fixture")
            (source / "AGENTS.md").write_text("<!-- coding-workflow:start -->\nold fixture guidance\n<!-- coding-workflow:end -->")
            (source / ".todo-orchestrator").mkdir()
            (source / ".todo-orchestrator/project.json").write_text(json.dumps({
                "configuration": {"workflow_front_door": "coding-workflow"}, "project_uuid": "fixed"
            }, sort_keys=True, indent=2) + "\n")
            commit_all(source, "fixture")
            with self.assertRaisesRegex(HARNESS.HarnessError, "outside its owned scope"):
                HARNESS.rehearse_migration(
                    source=source,
                    destination=temp / "clone",
                    dry_run_command=[sys.executable, str(MIGRATOR), "dry-run"],
                    apply_command=[sys.executable, str(MIGRATOR), "apply"],
                    remove_command=[sys.executable, str(MIGRATOR), "remove"],
                    allowed_paths=["AGENTS.md"],
                )

    def test_authority_sentinel_rejects_project_uuid_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = init_repo(Path(raw) / "fixture")
            (repo / "project.json").write_text(json.dumps({"project_uuid": "fixed", "configuration": {}}))
            commit_all(repo, "fixture")
            before = HARNESS.repository_sentinel(repo, immutable_json_fields={"project.json": ["project_uuid"]})
            (repo / "project.json").write_text(json.dumps({"project_uuid": "changed", "configuration": {}}))
            after = HARNESS.repository_sentinel(repo, immutable_json_fields={"project.json": ["project_uuid"]})
            with self.assertRaisesRegex(HARNESS.HarnessError, "authority state"):
                HARNESS.assert_authority_unchanged(before, after)


class EvidenceTests(unittest.TestCase):
    def test_evidence_redacts_secret_bearing_keys(self) -> None:
        value = HARNESS.redact({"status": "ok", "access_token": "not-for-evidence", "nested": {"capability": "opaque"}})
        self.assertEqual(value["status"], "ok")
        self.assertEqual(value["access_token"], "<redacted>")
        self.assertEqual(value["nested"]["capability"], "<redacted>")


if __name__ == "__main__":
    unittest.main()
