from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cuda_controller.py"


def test_legacy_run_request_is_refused_without_launching_payload(tmp_path: Path) -> None:
    marker = tmp_path / "payload-ran"
    spec = tmp_path / "job.json"
    spec.write_text(json.dumps({
        "schema_version": 1,
        "project_root": str(tmp_path),
        "argv": [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"],
    }), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "run", "--spec", str(spec), "--json"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )

    assert result.returncode == 2
    assert "retired" in result.stderr.lower()
    assert "device-scheduler job submit" in result.stderr
    assert "job get" in result.stderr
    assert not marker.exists()
