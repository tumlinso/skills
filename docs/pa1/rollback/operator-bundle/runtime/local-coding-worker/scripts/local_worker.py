#!/usr/bin/env python3
"""Compatibility CLI routed to Project Control's verified runtime."""
from __future__ import annotations
import runpy
from project_control.runtime_binding import bind_local_runtime

identity = bind_local_runtime()
runpy.run_path(str(identity.root / "scripts" / "local_worker.py"), run_name="__main__")
