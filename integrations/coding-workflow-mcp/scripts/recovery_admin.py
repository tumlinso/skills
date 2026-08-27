#!/usr/bin/env python3
"""Deprecated source-tree wrapper for coding-workflow-admin."""

from pathlib import Path
import sys


PACKAGE = Path(__file__).resolve().parents[1]
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from coding_workflow_mcp.admin import main  # noqa: E402


if __name__ == "__main__":
    main()
