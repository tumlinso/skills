#!/usr/bin/env python3
"""Read-only compatibility host inspection routed to the verified runtime."""
from __future__ import annotations
import runpy
from project_control.runtime_binding import bind_local_runtime

identity = bind_local_runtime()
runpy.run_path(str(identity.root / "scripts" / "inspect_host.py"), run_name="__main__")
