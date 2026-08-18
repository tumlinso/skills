#!/usr/bin/env python3
"""Emit build flags for GB200 NVL72-oriented Blackwell deployment."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "common" / "emit_arch_build_matrix.py"


if __name__ == "__main__":
    raise SystemExit(
        subprocess.call(
            [sys.executable, str(SCRIPT), "--system", "gb200-nvl72", "--embed-ptx", *sys.argv[1:]]
        )
    )
