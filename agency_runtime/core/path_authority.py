"""Process-local receipts for host-attested private filesystem namespaces."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from agency_runtime.core.filesystem_trust import absolute_path as _absolute

_AuthorityProbe = Callable[[Path], bool]
_AUTHORITIES: dict[Path, _AuthorityProbe] = {}
_LOCK = threading.RLock()
_RESOLUTION = threading.local()


def register_private_path_authority(root: Path, probe: _AuthorityProbe) -> None:
    """Register one exact in-process receipt-backed private namespace."""

    with _LOCK:
        _AUTHORITIES[_absolute(root)] = probe


def discard_private_path_authority(root: Path, probe: _AuthorityProbe | None = None) -> None:
    """Remove an authority only when its root and optional receipt still match."""

    normalized = _absolute(root)
    with _LOCK:
        if probe is None or _AUTHORITIES.get(normalized) is probe:
            _AUTHORITIES.pop(normalized, None)


def private_path_authority_covers(path: Path) -> bool:
    """Return whether a live receipt validates this exact descendant path."""

    target = _absolute(path)
    with _LOCK:
        authorities = tuple(_AUTHORITIES.items())
    for root, probe in authorities:
        try:
            target.relative_to(root)
        except ValueError:
            continue
        try:
            if probe(target):
                return True
        except Exception:
            pass

    # Process-local receipts intentionally do not cross an ``exec`` boundary.
    # A child running under Codex may independently re-attest the exact guarded
    # task scratch that contains its requested path.  The resolver validates
    # host/thread identity, native file identities, and current ACLs; it never
    # treats an inherited Agency path as authority by itself.
    if getattr(_RESOLUTION, "active", False):
        return False
    _RESOLUTION.active = True
    try:
        from agency_runtime.core.private_paths import (
            reattest_codex_host_private_path,
        )

        return reattest_codex_host_private_path(target)
    except Exception:
        return False
    finally:
        _RESOLUTION.active = False


__all__ = [
    "discard_private_path_authority",
    "private_path_authority_covers",
    "register_private_path_authority",
]
