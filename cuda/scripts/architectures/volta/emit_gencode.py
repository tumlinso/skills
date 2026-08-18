#!/usr/bin/env python3
"""Emit Volta-specific gencode flags."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "common" / "emit_arch_build_matrix.py"


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, str(SCRIPT), "--family", "volta", *sys.argv[1:]]))
