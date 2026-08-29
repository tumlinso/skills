from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install.py"
SPEC = importlib.util.spec_from_file_location("coding_workflow_install", SCRIPT)
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)
PACKAGE = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def test_prior_stdio_registration_round_trips_to_fixed_argv(self) -> None:
        registration = {
            "name": "coding-workflow",
            "transport": {
                "type": "stdio",
                "command": "/old/python",
                "args": ["-m", "old_entry"],
                "env": {"CODING_WORKFLOW_SKILLS_ROOT": "/old/skills"},
            },
        }
        self.assertEqual(installer._registration_args("codex", registration), [
            "codex", "mcp", "add", "coding-workflow", "--env",
            "CODING_WORKFLOW_SKILLS_ROOT=/old/skills", "--", "/old/python", "-m", "old_entry",
        ])

    def test_installer_uses_json_registration_and_protocol_smoke(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"get", SERVER_NAME, "--json"', source)
        self.assertIn('"list", "--json"', source)
        self.assertIn("_registration_args(codex, prior)", source)
        self.assertIn("coding_workflow_mcp.protocol", source)
        self.assertIn('"coding-workflow-admin"', source)
        self.assertIn('sterile_environment.pop("PYTHONPATH", None)', source)
        self.assertIn('"--inspect-only"', source)
        self.assertIn("skills-root.json", source)
        self.assertIn("shutil.copytree(venv_root, rollback_venv", source)
        self.assertIn("rollback_venv.rename(venv_root)", source)
        self.assertNotIn("shell=True", source)

    def test_installed_admin_can_resolve_canonical_source_from_xdg_locator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skills = root / "skills"
            (skills / "todo-orchestrator" / "todo_orchestrator").mkdir(parents=True)
            locator = root / "coding-workflow-mcp" / "skills-root.json"
            locator.parent.mkdir()
            locator.write_text(json.dumps({"skills_root": str(skills)}) + "\n", encoding="utf-8")
            import sys
            sys.path.insert(0, str(PACKAGE))
            from coding_workflow_mcp import runtime_identity
            environment = dict(os.environ)
            environment.pop("CODING_WORKFLOW_SKILLS_ROOT", None)
            environment["XDG_DATA_HOME"] = str(root)
            with patch.dict(os.environ, environment, clear=True):
                self.assertEqual(runtime_identity.locate_skills_root(), skills.resolve())


if __name__ == "__main__":
    unittest.main()
