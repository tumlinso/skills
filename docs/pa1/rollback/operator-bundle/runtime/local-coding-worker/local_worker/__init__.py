"""Legacy namespace bridge to Project Control's verified local runtime."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

_name = __name__
_placeholder = sys.modules.get(_name)
_spec = getattr(_placeholder, "__spec__", None)
_placeholder_file = getattr(_placeholder, "__file__", None)
if (_name != "local_worker" or _placeholder is None
        or not bool(getattr(_spec, "_initializing", False))
        or not _placeholder_file
        or Path(_placeholder_file).resolve() != Path(__file__).resolve()):
    raise ImportError("legacy_local_worker_package_placeholder_missing")
_foreign = [name for name in tuple(sys.modules)
            if name == "local_worker" or name.startswith("local_worker.")
            if name != _name]
if _foreign:
    raise ImportError("preloaded_local_worker_submodule_rejected")
if sys.modules.get(_name) is not _placeholder:
    raise ImportError("legacy_local_worker_placeholder_changed")
del sys.modules[_name]
try:
    from project_control.runtime_binding import bind_local_runtime

    _identity = bind_local_runtime()
    _canonical = importlib.import_module(_name)
    _origin = Path(str(getattr(_canonical, "__file__", ""))).resolve()
    if _identity.package_root != _origin.parent:
        raise ImportError("canonical_local_worker_origin_mismatch")
    if sys.modules.get(_name) is not _canonical:
        raise ImportError("canonical_local_worker_registry_mismatch")
except BaseException:
    # Restore only this initializer's own placeholder when binding failed.
    if _name not in sys.modules:
        sys.modules[_name] = _placeholder
    raise
# Import machinery returns the canonical package now stored under local_worker.
sys.modules[_name] = _canonical
