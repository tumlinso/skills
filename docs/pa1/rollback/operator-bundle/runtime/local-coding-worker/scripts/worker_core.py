"""Compatibility import for the retired top-level worker_core module."""
from __future__ import annotations
import hashlib
import json
import sys
import types
from pathlib import Path
from project_control.runtime_binding import bind_local_runtime

_name = __name__
_placeholder = sys.modules.get(_name)
_spec = getattr(_placeholder, "__spec__", None)
_placeholder_file = getattr(_placeholder, "__file__", None)
if (_name != "worker_core" or _placeholder is None
        or not bool(getattr(_spec, "_initializing", False))
        or not _placeholder_file
        or Path(_placeholder_file).resolve() != Path(__file__).resolve()):
    raise ImportError("legacy_worker_core_placeholder_missing")
_identity = bind_local_runtime()
_relative = "scripts/worker_core.py"
_manifest = json.loads((_identity.root / "receiver-manifest.json").read_text(encoding="utf-8"))
_expected = _manifest.get("files", {}).get(_relative)
_path = _identity.root / _relative
if not isinstance(_expected, str) or not _path.is_file():
    raise ImportError("canonical_worker_core_missing_from_manifest")
_source = _path.read_bytes()
if hashlib.sha256(_source).hexdigest() != _expected:
    raise ImportError("canonical_worker_core_hash_mismatch")
if sys.modules.get(_name) is not _placeholder:
    raise ImportError("legacy_worker_core_placeholder_changed")
del sys.modules[_name]
try:
    _canonical = types.ModuleType(_name)
    _canonical.__file__ = str(_path)
    _canonical.__package__ = ""
    _canonical.__spec__ = None
    sys.modules[_name] = _canonical
    exec(compile(_source, str(_path), "exec", dont_inherit=True), _canonical.__dict__)
except BaseException:
    if sys.modules.get(_name) is locals().get("_canonical"):
        del sys.modules[_name]
    if _name not in sys.modules:
        sys.modules[_name] = _placeholder
    raise
