"""Compatibility facade for transactional user configuration.

Schema validation, operation normalization, secret-free projection, and secure
persistence live in focused sibling modules. This facade intentionally keeps
the historic public and private seams used by the CLI, dashboard, and tests.
Write helpers resolve facade globals at call time so patching platform, ACL,
cache, or filesystem seams retains its original effect.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any

from agency_runtime.core import configuration_patch as _patch
from agency_runtime.core import configuration_persistence as _persistence
from agency_runtime.core import configuration_schema as _schema
from agency_runtime.core import configuration_service as _service
from agency_runtime.core.config import (
    config_to_yaml,
    load_config,
    reset_config_cache,
)
from agency_runtime.core.configuration_contracts import (
    ENV_OVERRIDE_PATHS,
    LOCK_TIMEOUT_SECONDS,
    MAX_CONFIG_BYTES,
    MAX_OPERATIONS,
    REDACTED,
    RESTART_REQUIRED_PATHS,
    ConfigConflictError,
    ConfigLockError,
    ConfigState,
    ConfigUpdateResult,
    ConfigurationError,
    ConfigValidationError,
)

# Historic constants remain available for integrations and monkeypatch-based
# platform tests. The implementation modules use the non-prefixed contracts.
_REDACTED = REDACTED
_IS_WINDOWS = os.name == "nt"
_MAX_CONFIG_BYTES = MAX_CONFIG_BYTES
_MAX_OPERATIONS = MAX_OPERATIONS
_LOCK_TIMEOUT_SECONDS = LOCK_TIMEOUT_SECONDS
_RESTART_REQUIRED_PATHS = RESTART_REQUIRED_PATHS
_ENV_OVERRIDE_PATHS = ENV_OVERRIDE_PATHS
_ENV_NAME = _schema._ENV_NAME
_PROVIDER_TYPES = _schema._PROVIDER_TYPES
_CLI_TRANSPORTS = _schema._CLI_TRANSPORTS
_PROFILES = _schema._PROFILES
_ENABLED_VALUES = _schema._ENABLED_VALUES
_SECRET_PARTS = _service._SECRET_PARTS
MAX_PROVIDER_CHAIN_ENTRIES = _schema.MAX_PROVIDER_CHAIN_ENTRIES
is_safe_cli_model_id = _schema.is_safe_cli_model_id
is_safe_credential_url = _schema.is_safe_credential_url


def resolve_config_path(path: str | Path | None = None) -> Path:
    return _persistence.resolve_config_path(path)


def _revision(raw: bytes) -> str:
    return _persistence.revision(raw)


def _read_raw(path: Path) -> bytes:
    return _persistence.read_raw(path)


def _parse_document(raw: bytes) -> dict[str, Any]:
    return _persistence.parse_document(raw)


def _read_document(path: Path) -> tuple[dict[str, Any], bytes]:
    return _persistence.read_document(path)


def read_config_revision(path: str | Path | None = None) -> str:
    """Return a secret-free revision even when the existing YAML is invalid."""

    return _revision(_read_raw(resolve_config_path(path)))


_secret_key = _service._secret_key
_redact = _service._redact
_secret_presence = _service._secret_presence


def _environment_overrides() -> dict[str, str]:
    return _service._environment_overrides()


def _effective_document(path: Path) -> dict[str, Any]:
    return _service.effective_document(
        path,
        load=load_config,
        render=config_to_yaml,
        validate=validate_config_document,
    )


def _state_from_document(path: Path, document: dict[str, Any], raw: bytes) -> ConfigState:
    return _service.state_from_document(
        path,
        document,
        raw,
        revision=_revision,
        effective=_effective_document,
        environment_overrides=_environment_overrides,
    )


def read_config_state(path: str | Path | None = None) -> ConfigState:
    """Read a consistent, fully redacted persisted/effective config snapshot."""

    return _service.read_config_state(
        path,
        resolve_path=resolve_config_path,
        read_document=_read_document,
        validate=validate_config_document,
        project=_state_from_document,
    )


# Preserve every historic schema helper as an importable facade seam.
_error = _schema._error
_mapping = _schema._mapping
_string = _schema._string
_boolean = _schema._boolean
_integer = _schema._integer
_number = _schema._number
_choice = _schema._choice
_env_name = _schema._env_name
_url = _schema._url
_loopback_host = _schema._loopback_host
_enabled = _schema._enabled
_string_list = _schema._string_list
_is_loopback_url = _schema._is_loopback_url
_validate_provider = _schema._validate_provider
_validate_providers = _schema._validate_providers
_validate_judge = _schema._validate_judge
_validate_ollama = _schema._validate_ollama
_validate_selector = _schema._validate_selector
_validate_canary = _schema._validate_canary
_validate_agents = _schema._validate_agents
_validate_store = _schema._validate_store
_validate_server = _schema._validate_server
_validate_dashboard = _schema._validate_dashboard
_validate_observability = _schema._validate_observability
_validate_adapter_entry = _schema._validate_adapter_entry
_validate_adapters = _schema._validate_adapters
_TOP_LEVEL_VALIDATORS = _schema._TOP_LEVEL_VALIDATORS
validate_config_document = _schema.validate_config_document
is_text_set_path = _patch.is_text_set_path

# Preserve operation helpers for downstream tests and integrations.
_set_validator = _patch._set_validator
_providers_for_operation = _patch._providers_for_operation
_nested_set = _patch._nested_set
_apply_provider_list = _patch._apply_provider_list
_secret_target = _patch._secret_target
_apply_secret_operation = _patch._apply_secret_operation
_enforce_local_only = _patch._enforce_local_only
_changed_restart_paths = _patch._changed_restart_paths
_diff_paths = _patch._diff_paths


def _complete_update(
    target: Path,
    *,
    original: dict[str, Any],
    original_raw: bytes,
    document: dict[str, Any],
    changed: set[str],
    policy_enforced: bool,
    force_write: bool = False,
    persist_document: Mapping[str, Any] | None = None,
) -> ConfigUpdateResult:
    return _service.complete_update(
        target,
        original=original,
        original_raw=original_raw,
        document=document,
        changed=changed,
        policy_enforced=policy_enforced,
        force_write=force_write,
        persist_document=persist_document,
        atomic_write=_atomic_write_yaml,
        reset_cache=reset_config_cache,
        read_document=_read_document,
        project=_state_from_document,
        changed_restart_paths=_changed_restart_paths,
    )


def apply_config_operations(
    operations: Sequence[Mapping[str, Any]],
    *,
    expected_revision: str,
    path: str | Path | None = None,
    locked_precondition: Callable[[], None] | None = None,
) -> ConfigUpdateResult:
    """Apply a typed operation batch as one locked, atomic transaction."""

    return _service.apply_config_operations(
        operations,
        expected_revision=expected_revision,
        path=path,
        validate_batch=_patch.validate_operation_batch,
        resolve_path=resolve_config_path,
        lock=_config_lock,
        read_document=_read_document,
        revision=_revision,
        validate=validate_config_document,
        apply=_patch.apply_operations,
        complete=_complete_update,
        narrow=_patch.narrowed_document,
        locked_precondition=locked_precondition,
    )


def replace_config_document(
    document: Mapping[str, Any],
    *,
    expected_revision: str,
    path: str | Path | None = None,
    recover_invalid_existing: bool = False,
) -> ConfigUpdateResult:
    """Replace the persisted document through the safe transaction path."""

    return _service.replace_config_document(
        document,
        expected_revision=expected_revision,
        path=path,
        recover_invalid_existing=recover_invalid_existing,
        resolve_path=resolve_config_path,
        lock=_config_lock,
        read_raw=_read_raw,
        revision=_revision,
        parse=_parse_document,
        validate=validate_config_document,
        enforce_policy=_enforce_local_only,
        diff_paths=_diff_paths,
        complete=_complete_update,
    )


def _restrict_windows_acl(path: Path, *, directory: bool = False) -> bool:
    return _persistence.restrict_windows_acl(
        path,
        directory=directory,
        is_windows=_IS_WINDOWS,
    )


def _is_link_or_reparse_point(path: Path) -> bool:
    return _persistence.is_link_or_reparse_point(path)


def _restrict_permissions(
    path: Path,
    *,
    required: bool = False,
    directory: bool = False,
) -> bool:
    return _persistence.restrict_permissions(
        path,
        required=required,
        directory=directory,
        is_windows=_IS_WINDOWS,
        windows_acl=_restrict_windows_acl,
        path_check=_is_link_or_reparse_point,
    )


def _ensure_config_parent(path: Path) -> None:
    _persistence.ensure_config_parent(
        path,
        restrict=_restrict_permissions,
        path_check=_is_link_or_reparse_point,
        is_windows=_IS_WINDOWS,
    )


def restrict_private_file(path: str | Path) -> None:
    """Apply the same owner-only file policy used by configuration writes."""

    _restrict_permissions(Path(path), required=True)


def restrict_private_directory(path: str | Path) -> None:
    """Apply the owner-only directory policy before sensitive child writes."""

    _restrict_permissions(Path(path), required=True, directory=True)


def _preflight_effective_candidate(path: Path) -> None:
    """Validate the exact secured candidate with active environment overlays.

    Validating against *this* source is necessary but not sufficient: hooks run
    the installed projection, not this code, and both config validators are
    strict allowlists. A CLI newer than the last install therefore writes a
    document only it can read, and every hook event fails afterwards. The
    candidate is checked against the installed projection too, before the
    atomic replace makes it the operator's live config.
    """

    reset_config_cache()
    try:
        _environment_overrides()
        _effective_document(path)
    finally:
        reset_config_cache()
    # Only the file the hooks actually read can break them. A candidate written
    # anywhere else -- a test fixture, an explicit --config elsewhere -- is not
    # something the installed projection will ever parse, and checking it would
    # make every such write depend on whatever happens to be installed on this
    # machine. The candidate is a temporary file beside its target, so its
    # parent is the target's directory.
    with suppress(OSError, ValueError):
        if path.parent != resolve_config_path(None).parent:
            return

    # Imported here: the guard reaches into launcher and runtime-staleness
    # modules that sit close to configuration, and a config write is rare
    # enough that the import cost never matters.
    from agency_runtime.core.installed_config_compatibility import (
        installed_projection_rejection,
    )

    rejection = installed_projection_rejection(path)
    if rejection:
        raise ConfigValidationError(rejection)


def _atomic_write_yaml(path: Path, document: Mapping[str, Any]) -> None:
    _persistence.atomic_write_yaml(
        path,
        document,
        ensure_parent=_ensure_config_parent,
        restrict=_restrict_permissions,
        preflight=_preflight_effective_candidate,
        path_check=_is_link_or_reparse_point,
        is_windows=_IS_WINDOWS,
    )


@contextmanager
def _config_lock(path: Path, *, timeout: float = _LOCK_TIMEOUT_SECONDS) -> Iterator[None]:
    with _persistence.config_lock(
        path,
        timeout=timeout,
        ensure_parent=_ensure_config_parent,
        restrict=_restrict_permissions,
        path_check=_is_link_or_reparse_point,
        is_windows=_IS_WINDOWS,
    ):
        yield


@contextmanager
def config_read_lock(
    path: str | Path | None = None,
    *,
    timeout: float = _LOCK_TIMEOUT_SECONDS,
) -> Iterator[Path]:
    """Serialize a config-bound Store operation with configuration writers."""

    target = resolve_config_path(path)
    with _config_lock(target, timeout=timeout):
        yield target


__all__ = [
    "ConfigConflictError",
    "ConfigLockError",
    "ConfigState",
    "ConfigUpdateResult",
    "ConfigValidationError",
    "ConfigurationError",
    "apply_config_operations",
    "config_read_lock",
    "is_text_set_path",
    "read_config_revision",
    "read_config_state",
    "replace_config_document",
    "resolve_config_path",
    "restrict_private_directory",
    "restrict_private_file",
    "validate_config_document",
]
