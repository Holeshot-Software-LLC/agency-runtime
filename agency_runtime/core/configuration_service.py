"""Secret-free projections and transaction orchestration for configuration."""

from __future__ import annotations

import copy
import math
import os
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

import yaml

from agency_runtime.core.configuration_contracts import (
    ENV_OVERRIDE_PATHS,
    REDACTED,
    ConfigConflictError,
    ConfigState,
    ConfigUpdateResult,
    ConfigValidationError,
)

_SECRET_PARTS = frozenset(
    {
        "api_key",
        "access_token",
        "auth_token",
        "client_secret",
        "password",
        "refresh_token",
        "secret",
        "token",
    }
)


def _secret_key(name: str) -> bool:
    normalized = name.strip().lower().replace("-", "_")
    if normalized.endswith("_env"):
        return False
    return normalized in _SECRET_PARTS or any(
        normalized.endswith(f"_{part}") for part in _SECRET_PARTS
    )


def _redact(value: Any, *, key: str = "") -> Any:
    if key and _secret_key(key):
        return REDACTED if value not in (None, "") else value
    if isinstance(value, dict):
        return {str(name): _redact(item, key=str(name)) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


def _secret_presence(document: Mapping[str, Any]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    judge = document.get("judge")
    if isinstance(judge, dict):
        result["judge.api_key"] = bool(judge.get("api_key"))
    providers = document.get("providers")
    if isinstance(providers, list):
        for index, provider in enumerate(providers):
            if isinstance(provider, dict):
                result[f"providers.{index}.api_key"] = bool(provider.get("api_key"))
    adapters = document.get("adapters")
    if isinstance(adapters, dict):
        litellm = adapters.get("litellm")
        if isinstance(litellm, dict):
            result["adapters.litellm.api_key"] = bool(litellm.get("api_key"))
    return result


def _environment_overrides() -> dict[str, str]:
    integer_rules = {
        "AGENCY_DASHBOARD_PORT": (1, 65535),
        "AGENCY_MAX_SELECTED": (1, 50),
        "AGENCY_RETENTION_DAYS": (1, 3650),
    }
    number_rules = {
        "AGENCY_JUDGE_TIMEOUT": (0.05, 60.0),
        "AGENCY_BYPASS_THRESHOLD": (0.0, 100.0),
    }
    for variable, (minimum, maximum) in integer_rules.items():
        raw = os.environ.get(variable, "").strip()
        if not raw:
            continue
        try:
            value = int(raw)
        except ValueError as exc:
            raise ConfigValidationError(f"{variable}: environment override is invalid") from exc
        if not minimum <= value <= maximum:
            raise ConfigValidationError(f"{variable}: environment override is invalid")
    for variable, (minimum, maximum) in number_rules.items():
        raw = os.environ.get(variable, "").strip()
        if not raw:
            continue
        try:
            value = float(raw)
        except ValueError as exc:
            raise ConfigValidationError(f"{variable}: environment override is invalid") from exc
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise ConfigValidationError(f"{variable}: environment override is invalid")
    capture = os.environ.get("AGENCY_CAPTURE_CONTENT", "").strip().lower()
    if capture and capture not in {
        "0",
        "1",
        "false",
        "true",
        "no",
        "yes",
        "off",
        "on",
    }:
        raise ConfigValidationError("AGENCY_CAPTURE_CONTENT: environment override is invalid")

    overrides = {
        path: variable for variable, path in ENV_OVERRIDE_PATHS if os.environ.get(variable, "")
    }
    if os.environ.get("LITELLM_API_KEY", "") and not os.environ.get("AGENCY_JUDGE_API_KEY", ""):
        overrides.setdefault("judge.api_key", "LITELLM_API_KEY")
    return overrides


def effective_document(
    path: Path,
    *,
    load: Callable[..., Any],
    render: Callable[..., str],
    validate: Callable[[Mapping[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Load and validate a fully rendered, secret-free effective document."""

    try:
        cfg = load(path=path, reload=True)
        rendered = yaml.safe_load(render(cfg, redact=True)) or {}
    except Exception as exc:
        # Loader exceptions may contain submitted scalar text, so expose only a
        # fixed message at this boundary.
        raise ConfigValidationError("configuration could not be loaded") from exc
    if not isinstance(rendered, dict):
        raise ConfigValidationError("effective configuration is invalid")
    try:
        return _redact(validate(rendered))
    except ConfigValidationError as exc:
        raise ConfigValidationError("effective configuration contains an invalid override") from exc


def state_from_document(
    path: Path,
    document: dict[str, Any],
    raw: bytes,
    *,
    revision: Callable[[bytes], str],
    effective: Callable[[Path], dict[str, Any]],
    environment_overrides: Callable[[], dict[str, str]] = _environment_overrides,
) -> ConfigState:
    """Build the redacted persisted/effective projection for one revision."""

    overrides = environment_overrides()
    return ConfigState(
        path=str(path),
        persisted=_redact(copy.deepcopy(document)),
        effective=effective(path),
        revision=revision(raw),
        secret_presence=_secret_presence(document),
        environment_overrides=overrides,
    )


def read_config_state(
    path: str | Path | None,
    *,
    resolve_path: Callable[[str | Path | None], Path],
    read_document: Callable[[Path], tuple[dict[str, Any], bytes]],
    validate: Callable[[Mapping[str, Any]], dict[str, Any]],
    project: Callable[[Path, dict[str, Any], bytes], ConfigState],
) -> ConfigState:
    """Read a consistent, fully redacted persisted/effective config snapshot."""

    target = resolve_path(path)
    for _attempt in range(3):
        document, raw = read_document(target)
        validate(document)
        state = project(target, document, raw)
        _latest_document, latest_raw = read_document(target)
        if raw == latest_raw:
            return state
    raise ConfigConflictError("configuration changed while it was being read; retry")


def complete_update(
    target: Path,
    *,
    original: dict[str, Any],
    original_raw: bytes,
    document: dict[str, Any],
    changed: set[str],
    policy_enforced: bool,
    atomic_write: Callable[[Path, Mapping[str, Any]], None],
    reset_cache: Callable[[], None],
    read_document: Callable[[Path], tuple[dict[str, Any], bytes]],
    project: Callable[[Path, dict[str, Any], bytes], ConfigState],
    changed_restart_paths: Callable[[set[str]], tuple[str, ...]],
    force_write: bool = False,
    persist_document: Mapping[str, Any] | None = None,
) -> ConfigUpdateResult:
    """Persist when necessary and project the committed transaction result.

    ``document`` is the normalized projection and stays the basis for change
    detection. ``persist_document``, when given, is what actually reaches disk:
    the same edit expressed against the operator's own file, without the
    defaults normalization would otherwise materialize into sections nobody
    touched. State is projected from a re-read either way.
    """

    if document == original and not force_write:
        changed.clear()
        saved_document = original
        saved_raw = original_raw
    else:
        atomic_write(target, document if persist_document is None else persist_document)
        reset_cache()
        saved_document, saved_raw = read_document(target)
    state = project(target, saved_document, saved_raw)
    return ConfigUpdateResult(
        state=state,
        changed_paths=tuple(sorted(changed)),
        restart_required=changed_restart_paths(changed),
        policy_enforced=policy_enforced,
    )


def apply_config_operations(
    operations: Sequence[Mapping[str, Any]],
    *,
    expected_revision: str,
    path: str | Path | None,
    validate_batch: Callable[[Sequence[Mapping[str, Any]]], None],
    resolve_path: Callable[[str | Path | None], Path],
    lock: Callable[[Path], AbstractContextManager[None]],
    read_document: Callable[[Path], tuple[dict[str, Any], bytes]],
    revision: Callable[[bytes], str],
    validate: Callable[[Mapping[str, Any]], dict[str, Any]],
    apply: Callable[
        [dict[str, Any], Sequence[Mapping[str, Any]]],
        tuple[dict[str, Any], set[str], bool],
    ],
    complete: Callable[..., ConfigUpdateResult],
    narrow: Callable[[Mapping[str, Any], Mapping[str, Any], set[str]], dict[str, Any] | None],
    locked_precondition: Callable[[], None] | None = None,
) -> ConfigUpdateResult:
    """Apply a typed operation batch as one locked, atomic transaction."""

    validate_batch(operations)
    if not isinstance(expected_revision, str) or not expected_revision.startswith("sha256:"):
        raise ConfigValidationError("expected revision is invalid")

    target = resolve_path(path)
    with lock(target):
        document, raw = read_document(target)
        if revision(raw) != expected_revision:
            raise ConfigConflictError("configuration changed; refresh before saving")
        # Kept before validation, which normalizes every default into place.
        pristine = copy.deepcopy(document)
        document = validate(document)
        if locked_precondition is not None:
            locked_precondition()
        original = copy.deepcopy(document)
        document, changed, policy_enforced = apply(document, operations)
        return complete(
            target,
            original=original,
            original_raw=raw,
            document=document,
            changed=changed,
            policy_enforced=policy_enforced,
            persist_document=narrow(pristine, document, changed),
        )


def replace_config_document(
    document: Mapping[str, Any],
    *,
    expected_revision: str,
    path: str | Path | None,
    recover_invalid_existing: bool,
    resolve_path: Callable[[str | Path | None], Path],
    lock: Callable[[Path], AbstractContextManager[None]],
    read_raw: Callable[[Path], bytes],
    revision: Callable[[bytes], str],
    parse: Callable[[bytes], dict[str, Any]],
    validate: Callable[[Mapping[str, Any]], dict[str, Any]],
    enforce_policy: Callable[[dict[str, Any]], bool],
    diff_paths: Callable[[Any, Any], set[str]],
    complete: Callable[..., ConfigUpdateResult],
) -> ConfigUpdateResult:
    """Replace the persisted document through the safe transaction path."""

    if not isinstance(document, Mapping):
        raise ConfigValidationError("configuration root must be a mapping")
    if not isinstance(expected_revision, str) or not expected_revision.startswith("sha256:"):
        raise ConfigValidationError("expected revision is invalid")

    target = resolve_path(path)
    with lock(target):
        raw = read_raw(target)
        if revision(raw) != expected_revision:
            raise ConfigConflictError("configuration changed; refresh before saving")
        recovered = False
        try:
            original = validate(parse(raw))
        except ConfigValidationError:
            if not recover_invalid_existing:
                raise
            original = {}
            recovered = True
        replacement = validate(copy.deepcopy(document))
        policy_enforced = enforce_policy(replacement)
        replacement = validate(replacement)
        changed = diff_paths(original, replacement)
        return complete(
            target,
            original=original,
            original_raw=raw,
            document=replacement,
            changed=changed,
            policy_enforced=policy_enforced,
            force_write=recovered,
        )
