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
    loaded = config or (load_config(config_path) if config_path is not None else load_config())
    if (
        config_path is None
        or not loaded.config_path
        or _canonical_path(config_path) != _canonical_path(frozen_config_path)
        or _canonical_path(loaded.config_path) != _canonical_path(frozen_config_path)
    ):
        raise StoreConfigBindingError("Store configuration identity changed; recreate Store")
    if config_derived and _canonical_path(loaded.store.resolved_path()) != _canonical_path(
        frozen_store_path
    ):
        raise StoreConfigBindingError("configured Store path changed; recreate Store")
    return loaded


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
    "config_for_store",
]
