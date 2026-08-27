from __future__ import annotations

from pathlib import Path
import unittest


class LivePublicContractTests(unittest.TestCase):
    def test_specialized_public_entry_points_remain_separate(self) -> None:
        root = Path(__file__).resolve().parents[3]
        paths = (
            "todo-orchestrator/scripts/todo.py",
            "cpp-context-compiler/scripts/ctxpp",
            "local-coding-worker/scripts/local_worker.py",
            "cuda/scripts/cuda_controller.py",
        )
        for relative in paths:
            self.assertTrue((root / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
