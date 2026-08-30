from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageMetadataTests(unittest.TestCase):
    def test_distribution_exports_only_the_canonical_package(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(metadata["project"]["name"], "todo-orchestrator")
        self.assertEqual(
            metadata["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"],
            ["todo_orchestrator"],
        )
        self.assertTrue((ROOT / "todo_orchestrator" / "__init__.py").is_file())
        self.assertNotIn("project_control", metadata["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"])

    def test_mcp_is_the_only_runtime_dependency(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(metadata["project"]["dependencies"], ["mcp[cli]>=1.0,<2"])


if __name__ == "__main__":
    unittest.main()
