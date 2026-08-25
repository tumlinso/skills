from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))

from local_worker.harnesses import QwenCodeAdapter


def outcome(**changes):
    value = {
        "outcome": "completed", "summary": "Inspected the source.", "claims": [],
        "changed_paths": [], "risk": "low", "blocker": None,
    }
    value.update(changes)
    return value


class QwenBindingTests(unittest.TestCase):
    def _session(self, root: Path, **config):
        binary = root / "qwen"
        binary.write_text(
            "#!/bin/sh\n"
            "for argument in \"$@\"; do\n"
            "  if [ \"$argument\" = \"--core4-unsupported-flag-probe\" ]; then\n"
            "    echo 'Unknown arguments: core4-unsupported-flag-probe' >&2\n"
            "    exit 1\n"
            "  fi\n"
            "done\n"
            "exit 0\n",
            encoding="utf-8",
        )
        binary.chmod(0o755)
        adapter = QwenCodeAdapter(str(binary))
        context = {
            "cwd": str(root), "runtime_dir": str(root / "runtime"),
            "repository_root": str(root), "base_url": "http://127.0.0.1:8080/v1",
            "model": "local-q4", "authorized_read_paths": ["src"],
        }
        context.update(config)
        handle = adapter.start(context)
        return adapter, adapter._session(handle)

    def test_environment_drops_remote_credentials_proxies_and_global_qwen_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter, session = self._session(root)
            with mock.patch.dict(os.environ, {
                "OPENAI_API_KEY": "remote", "HTTPS_PROXY": "remote-proxy",
                "QWEN_HOME": "/global/qwen", "PATH": "/bin", "LANG": "C.UTF-8",
            }, clear=True):
                _, additions = adapter.build_command(session, "bounded")
                environment = adapter.build_environment(session, additions)
            self.assertNotIn("OPENAI_API_KEY", environment)
            self.assertNotIn("HTTPS_PROXY", environment)
            self.assertEqual(environment["CORE4_LOCAL_API_KEY"], "core4-local")
            self.assertNotEqual(environment["QWEN_HOME"], "/global/qwen")

    def test_arbitrary_prose_is_never_completed(self):
        adapter = QwenCodeAdapter("qwen")
        result = adapter.normalize_outcome("looks good", {"core4": {}})
        self.assertEqual(result["status"], "needs_codex")
        self.assertIn("invalid_model_outcome", result["reason"])

    def test_readonly_completion_requires_valid_authorized_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / "src").mkdir(); source = root / "src" / "value.py"
            source.write_text("first\nsecond\n", encoding="utf-8")
            adapter, session = self._session(root)
            value = outcome(claims=[{"statement": "The second line exists.", "evidence": [{
                "path": "src/value.py", "line": 2, "end_line": 2,
                "content_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }]}])
            result = adapter.normalize_outcome(json.dumps(value), {"core4": {}}, session)
            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(result["model_outcome"]["changed_paths"], [])

    def test_readonly_normalizes_only_snapshot_local_absolute_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / "src").mkdir(); source = root / "src" / "value.py"
            source.write_text("value\n", encoding="utf-8")
            adapter, session = self._session(root)
            value = outcome(changed_paths=[str(source)], claims=[{
                "statement": "The value exists.",
                "evidence": [{"path": str(source), "line": 1, "end_line": 1}],
            }])
            result = adapter.normalize_outcome(json.dumps(value), {"core4": {}}, session)
            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(result["model_outcome"]["claims"][0]["evidence"][0]["path"], "src/value.py")
            self.assertEqual(result["model_outcome"]["changed_paths"], [])

    def test_writable_completion_uses_controller_observed_diff(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / "src").mkdir(); (root / "src" / "value.py").write_text("x\n")
            adapter, session = self._session(
                root, mode="writable", write_paths=["src"], actual_changed_paths=["src/value.py"],
            )
            value = outcome(changed_paths=["model/invented.py"])
            result = adapter.normalize_outcome(json.dumps(value), {"core4": {}}, session)
            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(result["model_outcome"]["changed_paths"], ["src/value.py"])

    def test_needs_codex_requires_blocker_and_no_patch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / "src").mkdir()
            adapter, session = self._session(root)
            valid = outcome(outcome="needs_codex", summary="Need semantic choice.", blocker="Public contract is ambiguous.")
            self.assertEqual(adapter.normalize_outcome(json.dumps(valid), {"core4": {}}, session)["status"], "needs_codex")
            invalid = outcome(outcome="needs_codex", summary="Need help.", blocker=None)
            self.assertIn("invalid_model_outcome", adapter.normalize_outcome(json.dumps(invalid), {"core4": {}}, session)["reason"])


if __name__ == "__main__":
    unittest.main()
