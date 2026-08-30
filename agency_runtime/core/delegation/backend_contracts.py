"""Delegation backend errors, protocol, and registry contracts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable


class BackendError(RuntimeError):
    """Base error carrying the normalized process result, when available."""

    def __init__(self, message: str, *, result: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.result = result or {}


class BackendUnavailableError(BackendError):
    """The configured executable cannot be launched on this host."""


class BackendTimeoutError(BackendError):
    """The host process exceeded the configured delegation deadline."""


class BackendExecutionError(BackendError):
    """The host process exited unsuccessfully."""


class BackendProtocolError(BackendError):
    """The host claimed process success but emitted an invalid response."""


@runtime_checkable
class DelegateBackend(Protocol):
    """Protocol implemented by delegation runtime adapters."""

    name: str

    def is_available(self) -> bool:
        """Return True when this backend can run on the current host."""

    def delegate(
        self,
        *,
        task: str,
        workdir: str | None = None,
        recommended_agent: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Dispatch one work unit and return backend-specific result data."""


class BackendRegistry:
    """Ordered registry of pluggable delegation backends."""

    def __init__(self, backends: Iterable[DelegateBackend] | None = None) -> None:
        self._backends: list[DelegateBackend] = list(backends or [])

    def register(self, backend: DelegateBackend) -> DelegateBackend:
        """Register a backend and return it for decorator-style use."""
        self._backends.append(backend)
        return backend

    def unregister(self, name: str) -> None:
        """Remove all backends with the given name."""
        self._backends = [backend for backend in self._backends if backend.name != name]

    def available_backends(self) -> list[DelegateBackend]:
        """Return currently available backends in selection order."""
        return [backend for backend in self._backends if self._is_available(backend)]

    @staticmethod
    def _is_available(backend: DelegateBackend) -> bool:
        try:
            return bool(backend.is_available())
        except Exception:
            return False

    def select_backend(self, *, preferred: str | None = None) -> DelegateBackend:
        """Select the first available backend, optionally constrained by name."""
        candidates = self._backends
        if preferred:
            candidates = [backend for backend in candidates if backend.name == preferred]
        for backend in candidates:
            if self._is_available(backend):
                return backend
        requested = f" named {preferred!r}" if preferred else ""
        details: list[str] = []
        for backend in candidates:
            availability = getattr(backend, "availability", None)
            if callable(availability):
                try:
                    record = availability()
                    details.append(f"{backend.name}: {record.get('reason') or 'unavailable'}")
                except Exception as exc:
                    details.append(
                        f"{backend.name}: availability check failed ({type(exc).__name__})"
                    )
            else:
                details.append(f"{backend.name}: unavailable")
        suffix = f" ({'; '.join(details)})" if details else ""
        raise BackendUnavailableError(f"No available delegation backend{requested}{suffix}")

    def delegate_func(self, *, preferred: str | None = None):
        """Return a delegate_func-compatible callable for lifecycle dispatch."""
        backend = self.select_backend(preferred=preferred)

        def _delegate(**kwargs: Any) -> Any:
            return backend.delegate(**kwargs)

        _delegate.backend_name = backend.name
        _delegate._agency_backend = backend
        return _delegate
