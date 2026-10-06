"""Acceptance checks for the one-way Skills to Project Control transition.

The tests use fresh interpreters for namespace and release checks. They verify
imports and metadata only; no supervisor, model server, or device is started.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import venv
from unittest import mock

from jsonschema import Draft202012Validator, ValidationError


PC_ROOT = Path(os.environ.get("PA1_PC_ROOT", "/home/tumlinson/project-control")).resolve()
SKILLS_ROOT = Path(os.environ.get("PA1_SKILLS_ROOT", "/home/tumlinson/.agents/skills")).resolve()
LEGACY_ROOT = Path(os.environ.get(
    "PA1_LEGACY_ROOT", str(SKILLS_ROOT / "local-coding-worker")
)).resolve()
RECEIVER_ROOT = Path(os.environ.get(
    "PA1_RECEIVER_ROOT", str(PC_ROOT / "src/project_control/local_runtime")
)).resolve()
TRANSITION_PATH = Path(os.environ.get(
    "PA1_TRANSITION_PATH", str(SKILLS_ROOT / "docs/pa1/rollback/runtime-transition.json")
)).resolve()
ROLLBACK_ROOT = Path(os.environ.get(
    "PA1_ROLLBACK_ROOT", str(SKILLS_ROOT / "docs/pa1/rollback")
)).resolve()
CATALOG_PATH = Path(os.environ.get(
    "PA1_CATALOG_PATH", str(SKILLS_ROOT / "integrations/native-skill-catalog.json")
)).resolve()
CATALOG_BASELINE = Path(os.environ.get(
    "PA1_CATALOG_BASELINE", str(SKILLS_ROOT / "docs/pa1/native-skill-catalog.baseline.json")
)).resolve()
RELEASE_CONSUMER = Path(os.environ.get(
    "PA1_RELEASE_CONSUMER", str(SKILLS_ROOT / "integrations/as1_release.py")
)).resolve()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_source_env(extra_path: list[Path]) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PROJECT_CONTROL_RELEASE_MANIFEST", None)
    env.pop("PROJECT_CONTROL_RELEASE_DIGEST", None)
    env["PYTHONPATH"] = os.pathsep.join(str(path) for path in extra_path)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_python(source: str, *, paths: list[Path], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", source], cwd=cwd,
        env=clean_source_env(paths), capture_output=True, text=True, check=False,
        timeout=30,
    )


def copy_project_control(package_root: Path) -> None:
    """Make a minimal isolated installed/source package for binding negatives."""
    package_root.mkdir(parents=True)
    shutil.copy2(PC_ROOT / "src/project_control/__init__.py", package_root / "__init__.py")
    shutil.copy2(PC_ROOT / "src/project_control/runtime_binding.py", package_root / "runtime_binding.py")
    shutil.copytree(RECEIVER_ROOT, package_root / "local_runtime")


def load_release_consumer():
    spec = importlib.util.spec_from_file_location("pa1_transition_as1_release", RELEASE_CONSUMER)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load release consumer: {RELEASE_CONSUMER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillsTransitionTests(unittest.TestCase):
    def test_legacy_and_receiver_entrypoints_share_canonical_module_identity(self):
        with tempfile.TemporaryDirectory(prefix="pa1-lcw-identity-") as raw:
            result = run_python(
                """
import importlib, json, sys
legacy = importlib.import_module('local_worker')
from project_control.runtime_binding import bind_local_runtime, import_local_worker_supervisor
identity = bind_local_runtime()
canonical = importlib.import_module('local_worker')
supervisor = import_local_worker_supervisor()
assert legacy is canonical is sys.modules['local_worker']
assert supervisor is sys.modules['local_worker.supervisor']
assert canonical.__name__ == 'local_worker'
assert supervisor.__name__ == 'local_worker.supervisor'
assert identity.package_root == __import__('pathlib').Path(canonical.__file__).resolve().parent
assert 'pc_trusted_observer_runtime' not in sys.modules
assert 'pc_as1_command_runtime' not in sys.modules
print(json.dumps({'identity': identity.fingerprint, 'root': str(identity.package_root)}))
""",
                paths=[LEGACY_ROOT, PC_ROOT / "src"], cwd=Path(raw),
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        observed = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(Path(observed["root"]).resolve(), RECEIVER_ROOT / "local_worker")

    def test_legacy_namespace_rejects_preloaded_foreign_submodule(self):
        with tempfile.TemporaryDirectory(prefix="pa1-lcw-poison-") as raw:
            result = run_python(
                """
import sys, types
sys.modules['local_worker.foreign'] = types.ModuleType('local_worker.foreign')
try:
    import local_worker
except ImportError as exc:
    assert 'preloaded_local_worker_submodule_rejected' in str(exc), str(exc)
else:
    raise AssertionError('foreign local_worker submodule was accepted')
""",
                paths=[LEGACY_ROOT, PC_ROOT / "src"], cwd=Path(raw),
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_receiver_source_drift_is_rejected_through_legacy_entrypoint(self):
        with tempfile.TemporaryDirectory(prefix="pa1-lcw-stale-") as raw:
            root = Path(raw) / "source-checkout"
            source = root / "src/project_control"
            copy_project_control(source)
            (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
            with (source / "local_runtime/local_worker/supervisor.py").open("ab") as stream:
                stream.write(b"\n# deliberately stale source fixture\n")
            result = run_python(
                """
try:
    import local_worker
except Exception as exc:
    assert 'receiver_file_hash_mismatch' in str(exc), repr(exc)
else:
    raise AssertionError('modified receiver source was accepted')
""",
                paths=[LEGACY_ROOT, root / "src"], cwd=Path(raw),
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_installed_legacy_import_fails_without_receiver_release_binding(self):
        with tempfile.TemporaryDirectory(prefix="pa1-lcw-unbound-install-") as raw:
            root = Path(raw)
            package = root / "site-packages/project_control"
            copy_project_control(package)
            release = root / "release-manifest.json"
            release.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            env = clean_source_env([LEGACY_ROOT, root / "site-packages"])
            env["PROJECT_CONTROL_RELEASE_MANIFEST"] = str(release)
            env["PROJECT_CONTROL_RELEASE_DIGEST"] = digest(release)
            result = subprocess.run(
                [sys.executable, "-c", "import local_worker"], cwd=root, env=env,
                capture_output=True, text=True, check=False, timeout=30,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime_release_binding_missing", result.stderr)

    def test_legacy_cli_scripts_forward_only_after_binding(self):
        for script_name in ("local_worker.py", "inspect_host.py"):
            with self.subTest(script=script_name), tempfile.TemporaryDirectory(prefix="pa1-lcw-cli-") as raw:
                script = LEGACY_ROOT / "scripts" / script_name
                target = RECEIVER_ROOT / "scripts" / script_name
                source = """
import pathlib, runpy
expected = pathlib.Path(__LEGACY_SCRIPT__)
target = pathlib.Path(__CANONICAL_TARGET__).resolve()
calls = []
def capture(path, *, run_name):
    calls.append((pathlib.Path(path).resolve(), run_name))
    raise RuntimeError('forward_target_captured')
runpy.run_path = capture
namespace = {'__name__': '__main__', '__file__': str(expected)}
try:
    exec(compile(expected.read_bytes(), str(expected), 'exec'), namespace)
except RuntimeError as exc:
    assert str(exc) == 'forward_target_captured'
else:
    raise AssertionError('forwarder did not dispatch')
assert calls == [(target, '__main__')]
""".replace("__LEGACY_SCRIPT__", repr(str(script))).replace(
    "__CANONICAL_TARGET__", repr(str(target))
)
                result = run_python(
                    source,
                    paths=[LEGACY_ROOT, PC_ROOT / "src"], cwd=Path(raw),
                )
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_worker_core_forwarder_exposes_receiver_source_only(self):
        with tempfile.TemporaryDirectory(prefix="pa1-lcw-worker-core-") as raw:
            result = run_python(
                """
import pathlib, sys
import worker_core
from project_control.runtime_binding import local_runtime_identity
identity = local_runtime_identity()
assert pathlib.Path(worker_core.__file__).resolve() == identity.root / 'scripts/worker_core.py'
assert worker_core.__name__ == 'worker_core'
assert not any(name.startswith('local_worker.controller') for name in sys.modules)
""",
                paths=[LEGACY_ROOT / "scripts", LEGACY_ROOT, PC_ROOT / "src"], cwd=Path(raw),
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_legacy_cli_denies_execution_integration_and_delegation_commands(self):
        script = LEGACY_ROOT / "scripts/local_worker.py"
        receiver_script = RECEIVER_ROOT / "scripts/local_worker.py"
        attempts = (
            ("run", "--request", "request.json"),
            ("integrate", "--request", "request.json"),
            ("delegate", "--claim-token", "toch_fixture_token", "--mode", "writable",
             "--target", "src/project_control/runtime_binding.py"),
            ("delegate", "--collect", "00000000-0000-0000-0000-000000000000"),
        )
        refusal_markers = ("invalid choice", "inactive", "disabled", "not supported", "retired")
        launcher = """
import pathlib, runpy, sys
legacy = pathlib.Path(sys.argv[1]).resolve()
receiver = pathlib.Path(sys.argv[2]).resolve()
args = sys.argv[3:]
real_run_path = runpy.run_path
calls = []
def forbidden(*unused, **kwargs):
    raise RuntimeError('forbidden command handler was reached')
def dispatch(path, *, run_name):
    if pathlib.Path(path).resolve() != receiver:
        return real_run_path(path, run_name=run_name)
    calls.append((pathlib.Path(path).resolve(), run_name))
    namespace = real_run_path(path, run_name='pa1_transition_sentinel')
    for name in ('run_controller', '_launch_delegate', '_run_detached_delegate', '_collect_delegate',
                 'IntegrationController', 'SupervisorClient'):
        if name in namespace:
            namespace[name] = forbidden
    sys.argv = [str(receiver), *args]
    try:
        status = namespace['main']()
    except SystemExit as error:
        status = error.code
    if calls != [(receiver, '__main__')]:
        raise AssertionError('legacy entrypoint did not reach the verified receiver')
    raise SystemExit(status)
runpy.run_path = dispatch
sys.argv = [sys.argv[0], str(legacy)]
namespace = {'__name__': '__main__', '__file__': str(legacy)}
exec(compile(legacy.read_bytes(), str(legacy), 'exec'), namespace)
"""
        with tempfile.TemporaryDirectory(prefix="pa1-lcw-denied-cli-") as raw:
            (Path(raw) / "request.json").write_text("{}\n", encoding="utf-8")
            for args in attempts:
                with self.subTest(command=args[0]):
                    result = subprocess.run(
                        [sys.executable, "-c", launcher, str(script), str(receiver_script), *args], cwd=raw,
                        env=clean_source_env([PC_ROOT / "src"]),
                        capture_output=True, text=True, check=False, timeout=30,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    combined = (result.stderr + "\n" + result.stdout).lower()
                    self.assertNotIn("forbidden command handler was reached", combined)
                    self.assertTrue(any(marker in combined for marker in refusal_markers), combined)

    def test_private_runtime_transition_preserves_rollback_and_authority_boundaries(self):
        transition = json.loads(TRANSITION_PATH.read_text(encoding="utf-8"))
        receipt_path = ROLLBACK_ROOT / "provenance.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        archive = receipt_path.parent / receipt["archive_path"]
        self.assertEqual(receipt["format"], "pa1-skills-runtime-rollback/1")
        self.assertEqual(digest(archive), receipt["archive_sha256"])
        self.assertEqual(
            len(receipt["archived_files"]) + len(receipt["excluded_unportable_bytecode"]),
            receipt["inventory_count"],
        )
        with tarfile.open(archive, "r:gz") as stream:
            members = {item.name: item for item in stream.getmembers() if item.isfile()}
            for name, member in members.items():
                parts = Path(name).parts
                self.assertFalse(Path(name).is_absolute() or ".." in parts, name)
        for entry in receipt["archived_files"]:
            matching = [member for name, member in members.items() if name.endswith("/" + entry["path"])]
            self.assertEqual(len(matching), 1, entry["path"])
            with tarfile.open(archive, "r:gz") as stream:
                content = stream.extractfile(matching[0]).read()
            self.assertEqual(len(content), entry["bytes"], entry["path"])
            self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"], entry["path"])
        touched = set(transition.get("add", [])) | set(transition.get("replace", [])) | set(transition.get("remove", []))
        self.assertTrue(touched)
        self.assertTrue(all(path.startswith("local-coding-worker/") for path in touched))
        exclusions = {item["id"]: item for item in transition["independent_authorities_preserved"]}
        for authority, relative in (
            ("todo-orchestrator", "todo-orchestrator"),
            ("cuda", "cuda"),
            ("cpp-context-compiler", "cpp-context-compiler"),
        ):
            with self.subTest(authority=authority):
                item = exclusions[authority]
                root = Path(item["supplier_path"]).resolve()
                self.assertTrue(root.is_dir())
                self.assertIn("no copies", item["operation"])
                self.assertFalse(any(path == relative or path.startswith(relative + "/") for path in touched))

    def test_catalog_delta_changes_only_local_worker_navigation_entry(self):
        baseline = json.loads(CATALOG_BASELINE.read_text(encoding="utf-8"))
        candidate = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        self.assertEqual({key: value for key, value in baseline.items() if key != "entries"},
                         {key: value for key, value in candidate.items() if key != "entries"})
        baseline_entries = {entry["name"]: entry for entry in baseline["entries"]}
        candidate_entries = {entry["name"]: entry for entry in candidate["entries"]}
        self.assertEqual(set(baseline_entries), set(candidate_entries))
        for name in set(baseline_entries) - {"local-coding-worker"}:
            self.assertEqual(candidate_entries[name], baseline_entries[name], name)
        legacy = candidate_entries["local-coding-worker"]
        expected = dict(baseline_entries["local-coding-worker"])
        expected["sha256"] = digest(LEGACY_ROOT / "SKILL.md")
        self.assertEqual(legacy, expected)

    def test_retired_schema_stubs_reject_and_receiver_contracts_still_validate(self):
        legacy_schemas = sorted((LEGACY_ROOT / "schemas").glob("*.schema.json"))
        receiver_schemas = RECEIVER_ROOT / "schemas"
        self.assertEqual(len(legacy_schemas), 8)
        instances = ({}, None, "request", 7, [])
        for path in legacy_schemas:
            with self.subTest(legacy_schema=path.name):
                schema = json.loads(path.read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(schema)
                self.assertEqual(schema["x-project-control-forward"],
                                 f"project_control/local_runtime/schemas/{path.name}")
                validator = Draft202012Validator(schema)
                for instance in instances:
                    with self.subTest(instance_type=type(instance).__name__):
                        with self.assertRaises(ValidationError):
                            validator.validate(instance)

        repo_root = str(PC_ROOT)
        common = {
            "backend": "fake", "role": "explain", "readonly": True,
            "repo_root": repo_root, "child_token": "toch_fixture_token",
            "objective": "Explain a read-only contract fixture.",
            "scopes": ["src/project_control/runtime_binding.py"],
            "target": "local_runtime_identity", "intent": "understand",
            "budget_tokens": 1024, "max_items": 4,
        }
        valid_requests = {
            "delegation-spec-v1.schema.json": {
                **common, "format": "LCW-REQUEST/1", "schema_version": 1,
            },
            "delegation-spec-v2.schema.json": {
                **common, "format": "LCW-REQUEST/2", "schema_version": 2,
                "execution": {"backend": "fake", "harness": "codex", "gpu_count": 1},
            },
        }
        for name, request in valid_requests.items():
            with self.subTest(receiver_schema=name):
                schema = json.loads((receiver_schemas / name).read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(schema)
                Draft202012Validator(schema).validate(request)

    def test_candidate_release_requires_and_executes_receiver_source_pins(self):
        consumer = load_release_consumer()
        with tempfile.TemporaryDirectory(prefix="pa1-lcw-candidate-") as raw:
            candidate = Path(raw) / "candidate"
            venv.EnvBuilder(with_pip=False, clear=True).create(candidate)
            package = candidate / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages/project_control"
            copy_project_control(package)
            shadow = Path(raw) / "shadow"
            (shadow / "project_control").mkdir(parents=True)
            (shadow / "project_control/__init__.py").write_text("", encoding="utf-8")
            (shadow / "project_control/runtime_binding.py").write_text(
                "from types import SimpleNamespace\n"
                "def bind_local_runtime():\n"
                "    return SimpleNamespace(manifest_sha256='0'*64, fingerprint='0'*64, root='/shadow')\n",
                encoding="utf-8",
            )
            manifest = candidate / "release-manifest.json"
            manifest.write_text("{}\n", encoding="utf-8")
            receiver_manifest = package / "local_runtime/receiver-manifest.json"
            manifest_data = json.loads(receiver_manifest.read_text(encoding="utf-8"))
            fingerprint = hashlib.sha256(json.dumps(
                manifest_data["files"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")).hexdigest()
            skills_root = candidate / "runtime-skills"
            skills_root.mkdir()
            installed = {
                "schema_version": 2,
                "project_control_commit": "fixture-project-control",
                "todo_commit": "fixture-skills",
                "skills_root": str(skills_root),
                "frozen_skill_resources": {},
                "local_runtime_binding": {
                    "path": "project_control/local_runtime",
                    "manifest_sha256": digest(receiver_manifest), "fingerprint": fingerprint,
                },
            }
            manifest.write_text(json.dumps(installed, sort_keys=True) + "\n", encoding="utf-8")
            # The candidate probe must use its own installed package even when
            # the caller carries a conflicting checkout on PYTHONPATH.
            try:
                with mock.patch.dict(os.environ, {"PYTHONPATH": str(shadow)}):
                    pins = consumer.validate_receiver(candidate, installed, manifest)
            except subprocess.CalledProcessError as error:
                self.fail(f"candidate receiver probe failed: {error.stderr}\n{error.stdout}")
            self.assertEqual(pins, {"manifest_sha256": digest(receiver_manifest), "fingerprint": fingerprint})

            old_release = {"schema_version": 2}
            with self.assertRaisesRegex(ValueError, "no Project Control local runtime binding"):
                consumer.validate_receiver(candidate, old_release, manifest)

            stale = dict(installed)
            stale["local_runtime_binding"] = dict(installed["local_runtime_binding"], fingerprint="0" * 64)
            with self.assertRaisesRegex(ValueError, "another receiver fingerprint"):
                consumer.validate_receiver(candidate, stale, manifest)

            stale_file = Path(raw) / "stale-release.json"
            stale_file.write_text(json.dumps(stale), encoding="utf-8")
            optimized_probe = r'''
import importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("optimized_candidate_consumer", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
candidate, release_path, manifest = Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
release = json.loads(release_path.read_text())
try:
    module.validate_receiver(candidate, release, manifest)
except ValueError as error:
    if "another receiver fingerprint" not in str(error):
        raise SystemExit(f"unexpected validation error: {error}")
else:
    raise SystemExit("wrong receiver fingerprint accepted under -O")
'''
            optimized = subprocess.run(
                [sys.executable, "-O", "-c", optimized_probe, str(RELEASE_CONSUMER),
                 str(candidate), str(stale_file), str(manifest)],
                cwd=PC_ROOT, capture_output=True, text=True, check=False, timeout=30,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            self.assertEqual(
                optimized.returncode, 0,
                f"optimized receiver pin check failed: stdout={optimized.stdout!r} stderr={optimized.stderr!r}",
            )

            consumer.SKILLS = SKILLS_ROOT
            instructions = SKILLS_ROOT / "planning/adaptive-surface-v1/PAIRED_RELEASE.md"
            release = {
                "format": "skills-as1-paired-release/1",
                "candidate": {"path": str(candidate), "manifest_sha256": digest(manifest)},
                "pins": {"project_control": installed["project_control_commit"],
                         "skills": installed["todo_commit"]},
                "instructions": {"path": "planning/adaptive-surface-v1/PAIRED_RELEASE.md",
                                 "sha256": digest(instructions)},
            }
            with mock.patch.dict(os.environ, {"PYTHONPATH": str(shadow)}):
                observed_candidate = consumer.validate_identity(release)
            self.assertIsInstance(observed_candidate, Path)
            self.assertEqual(observed_candidate.name, candidate.name)

    def test_release_consumer_validation_survives_optimized_python(self):
        """Security-relevant validation must not disappear under ``python -O``."""
        source = r'''
import importlib.util
import sys
from pathlib import Path

path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("optimized_release_consumer", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def must_reject(label, callback):
    try:
        callback()
    except ValueError:
        return
    except Exception as error:
        raise SystemExit(f"{label}: unexpected exception {type(error).__name__}: {error}")
    raise SystemExit(f"{label}: invalid input was accepted")

required = {"SQA-01", "SQA-02", "SQA-03"}
must_reject("pytest-exitstatus", lambda: module.passing_cases(
    {"pytest_exitstatus": 1, "cases": {}}, required))
must_reject("failed-or-missing-sqa", lambda: module.passing_cases(
    {"pytest_exitstatus": 0, "cases": {
        "SQA-01": [{"outcome": "passed"}],
        "SQA-02": [{"outcome": "failed"}],
    }}, required))

# Exercise the real release proof identity gate while isolating filesystem and
# live-consumer dependencies. Every preceding proof field is valid; only the
# receiver fingerprint differs from the candidate binding.
candidate = Path("/candidate")
receiver = {"manifest_sha256": "m" * 64, "fingerprint": "f" * 64}
module._validate_identity = lambda release: (candidate, receiver)
qualification = {"pytest_exitstatus": 0, "cases": {
    name: [{"outcome": "passed"}] for name in required
}}
proof = {
    "format": "as1-paired-realproof/1", "status": "passed",
    "source_identity": {
        "candidate_root": str(candidate), "pc_commit": "pc", "skills_commit": "skills",
        "release_sha256": "r" * 64, "receiver_manifest_sha256": "m" * 64,
        "receiver_fingerprint": "0" * 64,
    },
}
module.read_bound = lambda reference: (
    Path("/proof.json"), qualification if reference == "qualification" else proof)
release = {
    "status": "passed", "candidate": {"manifest_sha256": "r" * 64},
    "pins": {"project_control": "pc", "skills": "skills"},
    "evidence": {"skills_qualification": "qualification", "skills_real_proof": "proof"},
}
must_reject("wrong-proof-receiver-fingerprint", lambda: module.validate_release(release))
'''
        result = subprocess.run(
            [sys.executable, "-O", "-c", source, str(RELEASE_CONSUMER)],
            cwd=PC_ROOT, capture_output=True, text=True, check=False, timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(
            result.returncode, 0,
            f"optimized release checks failed: stdout={result.stdout!r} stderr={result.stderr!r}",
        )


if __name__ == "__main__":
    unittest.main()
