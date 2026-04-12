import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scaffold_ncurses_app.py"


def run_scaffold(output_dir: Path, app_name: str, language: str) -> Path:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-dir",
            str(output_dir),
            "--app-name",
            app_name,
            "--language",
            language,
        ],
        capture_output=True,
        check=True,
        text=True,
    )
    return Path(result.stdout.strip())


class ScaffoldNcursesAppTests(unittest.TestCase):
    def test_c_scaffold_contains_core_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = run_scaffold(Path(tmpdir), "Monitor", "c")
            text = output.read_text(encoding="utf-8")
            self.assertTrue(output.name.endswith(".c"))
            self.assertIn("typedef struct {", text)
            self.assertIn("static Layout compute_layout(void)", text)
            self.assertIn("static void handle_key(AppState *state, int ch)", text)
            self.assertIn("KEY_RESIZE", text)
            self.assertIn("restore_terminal();", text)

    def test_cpp_scaffold_uses_raii_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = run_scaffold(Path(tmpdir), "Browser", "cpp")
            text = output.read_text(encoding="utf-8")
            self.assertEqual(output.name, "main.cpp")
            self.assertIn("class TerminalSession", text)
            self.assertIn("auto compute_layout() -> Layout", text)
            self.assertIn("void handle_key(AppState& state, int ch)", text)
            self.assertIn("KEY_RESIZE", text)


if __name__ == "__main__":
    unittest.main()
