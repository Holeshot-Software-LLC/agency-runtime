"""Shared HTTP transport-failure classification for loopback servers."""

from __future__ import annotations

import errno

_EXPECTED_CLIENT_DISCONNECT_ERRNOS = frozenset(
    value
    for value in (
        getattr(errno, "ECONNABORTED", None),
        getattr(errno, "ECONNRESET", None),
        getattr(errno, "EPIPE", None),
        getattr(errno, "ESHUTDOWN", None),
        getattr(errno, "ENOTCONN", None),
    )
    if value is not None
)
_EXPECTED_CLIENT_DISCONNECT_WINERRORS = frozenset(
    {
        10053,  # WSAECONNABORTED
        10054,  # WSAECONNRESET
        10058,  # WSAESHUTDOWN
    }
)


def is_expected_client_disconnect(exc: BaseException) -> bool:
    """Return whether response I/O failed because the HTTP client went away."""

    if isinstance(exc, (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)):
        return True
    if not isinstance(exc, OSError):
        return False
    return (
        exc.errno in _EXPECTED_CLIENT_DISCONNECT_ERRNOS
        or getattr(exc, "winerror", None) in _EXPECTED_CLIENT_DISCONNECT_WINERRORS
    )


__all__ = ["is_expected_client_disconnect"]
