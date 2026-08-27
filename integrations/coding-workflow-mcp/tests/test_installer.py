from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install.py"
SPEC = importlib.util.spec_from_file_location("coding_workflow_install", SCRIPT)
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


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
        self.assertNotIn("shell=True", source)


if __name__ == "__main__":
    unittest.main()
