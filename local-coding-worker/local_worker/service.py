from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol


class AdapterError(RuntimeError):
    pass


class LifecycleAdapter(Protocol):
    def inspect(self) -> dict[str, Any]: ...
    def start(self, context: dict[str, Any]) -> str: ...
    def health(self, handle: str) -> dict[str, Any]: ...
    def run(self, handle: str, request: dict[str, Any]) -> dict[str, Any]: ...
    def cancel(self, handle: str, request_id: str | None = None) -> dict[str, Any]: ...
    def drain(self, handle: str) -> dict[str, Any]: ...
    def evict(self, handle: str) -> dict[str, Any]: ...
    def usage(self, handle: str) -> dict[str, Any]: ...


class AdapterService:
    """Small registry over replaceable adapters; it owns no work truth."""

    def __init__(self) -> None:
        self._adapters: dict[str, LifecycleAdapter] = {}

    def register(self, name: str, adapter: LifecycleAdapter) -> None:
        if not name or name in self._adapters:
            raise AdapterError(f"adapter name is empty or already registered: {name!r}")
        self._adapters[name] = adapter

    def inspect(self) -> dict[str, Any]:
        return {name: adapter.inspect() for name, adapter in sorted(self._adapters.items())}

    def _adapter(self, name: str) -> LifecycleAdapter:
        try:
            return self._adapters[name]
        except KeyError as error:
            raise AdapterError(f"unknown adapter: {name}") from error

    def start(self, name: str, context: dict[str, Any]) -> str:
        return self._adapter(name).start(context)

    def health(self, name: str, handle: str) -> dict[str, Any]:
        return self._adapter(name).health(handle)

    def run(self, name: str, handle: str, request: dict[str, Any]) -> dict[str, Any]:
        return self._adapter(name).run(handle, request)

    def cancel(self, name: str, handle: str, request_id: str | None = None) -> dict[str, Any]:
        return self._adapter(name).cancel(handle, request_id)

    def drain(self, name: str, handle: str) -> dict[str, Any]:
        return self._adapter(name).drain(handle)

    def evict(self, name: str, handle: str) -> dict[str, Any]:
        return self._adapter(name).evict(handle)

    def usage(self, name: str, handle: str) -> dict[str, Any]:
        return self._adapter(name).usage(handle)


@contextmanager
def disposable_task_context(prefix: str = "local-worker-task-") -> Iterator[Path]:
    """Yield isolated runtime state and remove it on every exit path."""
    with tempfile.TemporaryDirectory(prefix=prefix) as temporary:
        root = Path(temporary)
        (root / "runtime").mkdir()
        yield root
