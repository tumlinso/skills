from __future__ import annotations

from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from coding_workflow_mcp.handles import CapabilityStore
from coding_workflow_mcp.server import create_server
from test_tools import FakeBackend


_temporary = tempfile.TemporaryDirectory()
_root = Path(_temporary.name).resolve()
_backend = FakeBackend(_root, CapabilityStore(_root / "state"))

create_server(_backend).run(transport="stdio")

