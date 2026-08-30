"""Configuration identity helpers for Store-backed runtime operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agency_runtime.core.config import AgencyConfig, load_config


class StoreConfigBindingError(RuntimeError):
    """Signal that a long-lived Store no longer matches its live config."""


def _canonical_path(value: str | os.PathLike[str]) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(Path(value).expanduser())))


def _assert_store_database_identity(store: Any) -> None:
    """Reject mutation of a canonical Store's public database target."""

    frozen_db_path = getattr(store, "_frozen_db_path", None)
    binding_fields = (
        getattr(store, "_configured_config_path", None),
        getattr(store, "_configured_store_path", None),
        getattr(store, "_store_path_config_derived", None),
    )
    if frozen_db_path is None:
        if any(value is not None for value in binding_fields):
            raise StoreConfigBindingError(
                "Store configuration binding is incomplete; recreate Store"
            )
        return
    current_db_path = getattr(store, "db_path", None)
    if current_db_path is None:
        raise StoreConfigBindingError("Store database identity is missing; recreate Store")
    try:
        unchanged = _canonical_path(current_db_path) == _canonical_path(frozen_db_path)
    except (OSError, TypeError, ValueError):
        unchanged = False
    if not unchanged:
        raise StoreConfigBindingError("Store database identity changed; recreate Store")


def assert_store_config_binding(
    store: Any,
    config: AgencyConfig | None = None,
) -> AgencyConfig:
    """Return live config only when a real Store still owns its birth target.

    Store-like test doubles and embedders predating the binding contract do not
    expose the private frozen identities and retain their compatibility. Every
    canonical :class:`Store` captures both identities during construction.
    """

    _assert_store_database_identity(store)
    config_path = getattr(store, "config_path", None)
    frozen_config_path = getattr(store, "_configured_config_path", None)
    frozen_store_path = getattr(store, "_configured_store_path", None)
    config_derived = getattr(store, "_store_path_config_derived", None)
    if frozen_config_path is None and frozen_store_path is None and config_derived is None:
        return config or (load_config(config_path) if config_path is not None else load_config())
    if (
        frozen_config_path is None
        or frozen_store_path is None
        or not isinstance(config_derived, bool)
    ):
        raise StoreConfigBindingError("Store configuration binding is incomplete; recreate Store")
    try:
        config_identity_matches = config_path is not None and _canonical_path(
            config_path
        ) == _canonical_path(frozen_config_path)
    except (OSError, TypeError, ValueError):
        config_identity_matches = False
    if not config_identity_matches:
        raise StoreConfigBindingError("Store configuration identity changed; recreate Store")
    loaded = config or load_config(frozen_config_path)
    if not loaded.config_path or _canonical_path(loaded.config_path) != _canonical_path(
        frozen_config_path
    ):
        raise StoreConfigBindingError("Store configuration identity changed; recreate Store")
    if config_derived and _canonical_path(loaded.store.resolved_path()) != _canonical_path(
        frozen_store_path
    ):
        raise StoreConfigBindingError("configured Store path changed; recreate Store")
    return loaded


def assert_store_requested_runtime_identity(
    store: Any,
    *,
    config_path: str | os.PathLike[str] | None = None,
    db_path: str | os.PathLike[str] | None = None,
) -> None:
    """Compare redundant server paths to frozen Store identities without I/O.

    An injected Store and explicit path arguments are accepted only when the
    Store exposes the canonical binding contract and both supplied identities
    match. Legacy unbound Store-like objects remain supported when callers do
    not also supply path arguments; an unverifiable mixed form is rejected.
    """

    if config_path is None and db_path is None:
        return
    _assert_store_database_identity(store)
    frozen_config_path = getattr(store, "_configured_config_path", None)
    frozen_store_path = getattr(store, "_configured_store_path", None)
    config_derived = getattr(store, "_store_path_config_derived", None)
    public_config_path = getattr(store, "config_path", None)
    frozen_db_path = getattr(store, "_frozen_db_path", None)
    public_db_path = getattr(store, "db_path", None)
    if (
        frozen_config_path is None
        or frozen_store_path is None
        or not isinstance(config_derived, bool)
        or frozen_db_path is None
    ):
        raise StoreConfigBindingError(
            "injected Store does not expose a verifiable runtime identity"
        )
    try:
        store_identity_matches = (
            public_config_path is not None
            and public_db_path is not None
            and _canonical_path(public_config_path) == _canonical_path(frozen_config_path)
            and _canonical_path(public_db_path) == _canonical_path(frozen_db_path)
        )
        requested_config_matches = config_path is None or _canonical_path(
            config_path
        ) == _canonical_path(frozen_config_path)
        requested_db_matches = db_path is None or _canonical_path(db_path) == _canonical_path(
            frozen_db_path
        )
    except (OSError, TypeError, ValueError):
        store_identity_matches = False
        requested_config_matches = False
        requested_db_matches = False
    if not store_identity_matches:
        raise StoreConfigBindingError("Store runtime identity changed; recreate Store")
    if not requested_config_matches or not requested_db_matches:
        raise StoreConfigBindingError(
            "requested runtime identity does not match Store; recreate Store"
        )


def config_for_store(
    store: Any,
    config: AgencyConfig | None = None,
) -> AgencyConfig:
    """Return explicit immutable config or one binding-checked live snapshot."""

    if config is not None:
        _assert_store_database_identity(store)
        return config
    return assert_store_config_binding(store)


__all__ = [
    "StoreConfigBindingError",
    "assert_store_config_binding",
    "assert_store_requested_runtime_identity",
    "config_for_store",
]
