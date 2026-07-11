"""Transactional, typed mutation of the user configuration file.

This module is the integration boundary shared by command-line and dashboard
configuration surfaces.  Callers should:

* use :func:`read_config_state` to obtain a redacted persisted/effective view
  and its optimistic-concurrency revision;
* submit only operation dictionaries to :func:`apply_config_operations`; and
* return the resulting :class:`ConfigState` directly rather than re-reading or
  serializing unredacted YAML.

The module deliberately never returns direct credential values.  Secret
operations use explicit ``preserve``, ``replace``, and ``clear`` actions so a
redaction marker can never be written back as a credential.  File replacement
is atomic, owner-restricted, and protected by a short cross-process lock on
native Windows and POSIX systems.
"""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import math
import os
import re
import stat
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence
from urllib.parse import urlsplit

import yaml

from agency_runtime.core.config import config_to_yaml, load_config, reset_config_cache


_REDACTED = "***REDACTED***"
_IS_WINDOWS = os.name == "nt"
_MAX_CONFIG_BYTES = 1024 * 1024
_MAX_OPERATIONS = 128
_LOCK_TIMEOUT_SECONDS = 5.0
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROVIDER_TYPES = frozenset(
    {"openai", "openai-compatible", "anthropic", "ollama", "litellm"}
)
_PROFILES = frozenset({"local-only", "standard", "power", "yolo"})
_ENABLED_VALUES = frozenset({"auto", "true", "false"})
_RESTART_REQUIRED_PATHS = (
    "store.db_path",
    "server.host",
    "server.port",
    "server.max_body_size",
    "dashboard.port",
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

_ENV_OVERRIDE_PATHS: tuple[tuple[str, str], ...] = (
    ("AGENCY_JUDGE_MODEL", "judge.model"),
    ("AGENCY_JUDGE_BASE_URL", "judge.base_url"),
    ("AGENCY_JUDGE_API_KEY", "judge.api_key"),
    ("AGENCY_JUDGE_TIMEOUT", "judge.timeout"),
    ("AGENCY_MAX_SELECTED", "judge.max_selected"),
    ("AGENCY_BYPASS_THRESHOLD", "judge.confidence_bypass_threshold"),
    ("OLLAMA_BASE_URL", "ollama.base_url"),
    ("AGENCY_OLLAMA_FALLBACK_MODEL", "ollama.model"),
    ("AGENCY_DB_PATH", "store.db_path"),
    ("AGENCY_DASHBOARD_PORT", "dashboard.port"),
    ("AGENCY_CAPTURE_CONTENT", "observability.capture_content"),
    ("AGENCY_RETENTION_DAYS", "observability.retention_days"),
    ("AGENCY_PROFILE", "profile"),
    ("LITELLM_API_KEY", "adapters.litellm.api_key"),
)


class ConfigurationError(ValueError):
    """Base class for safe, value-free configuration errors."""


class ConfigValidationError(ConfigurationError):
    """The requested document or operation does not satisfy the schema."""


class ConfigConflictError(ConfigurationError):
    """The persisted document changed after the caller read its revision."""


class ConfigLockError(ConfigurationError):
    """The configuration lock could not be acquired before its deadline."""


@dataclass(frozen=True, slots=True)
class ConfigState:
    """Secret-free state suitable for a CLI JSON response or dashboard API."""

    path: str
    persisted: dict[str, Any]
    effective: dict[str, Any]
    revision: str
    secret_presence: dict[str, bool]
    environment_overrides: dict[str, str]
    restart_required_paths: tuple[str, ...] = _RESTART_REQUIRED_PATHS


@dataclass(frozen=True, slots=True)
class ConfigUpdateResult:
    """Result of one locked, validated, atomic update transaction."""

    state: ConfigState
    changed_paths: tuple[str, ...]
    restart_required: tuple[str, ...]
    policy_enforced: bool


def resolve_config_path(path: str | Path | None = None) -> Path:
    """Resolve the write target, including a nonexistent env-overridden path."""

    if path is not None:
        return Path(path).expanduser()
    configured = os.environ.get("AGENCY_CONFIG_PATH", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".agency-runtime" / "agency.yaml"


def _revision(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _read_raw(path: Path) -> bytes:
    if not path.exists():
        return b""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigurationError("configuration file could not be read") from exc
    if len(raw) > _MAX_CONFIG_BYTES:
        raise ConfigValidationError("configuration file exceeds the size limit")
    return raw


def _parse_document(raw: bytes) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(raw)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ConfigValidationError(
            "configuration file is not valid UTF-8 YAML"
        ) from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigValidationError("configuration root must be a mapping")
    return loaded


def _read_document(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = _read_raw(path)
    return _parse_document(raw), raw


def read_config_revision(path: str | Path | None = None) -> str:
    """Return a secret-free revision even when the existing YAML is invalid."""

    return _revision(_read_raw(resolve_config_path(path)))


def _secret_key(name: str) -> bool:
    normalized = name.strip().lower().replace("-", "_")
    if normalized.endswith("_env"):
        return False
    return normalized in _SECRET_PARTS or any(
        normalized.endswith(f"_{part}") for part in _SECRET_PARTS
    )


def _redact(value: Any, *, key: str = "") -> Any:
    if key and _secret_key(key):
        return _REDACTED if value not in (None, "") else value
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
            raise ConfigValidationError(
                f"{variable}: environment override is invalid"
            ) from exc
        if not minimum <= value <= maximum:
            raise ConfigValidationError(f"{variable}: environment override is invalid")
    for variable, (minimum, maximum) in number_rules.items():
        raw = os.environ.get(variable, "").strip()
        if not raw:
            continue
        try:
            value = float(raw)
        except ValueError as exc:
            raise ConfigValidationError(
                f"{variable}: environment override is invalid"
            ) from exc
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise ConfigValidationError(f"{variable}: environment override is invalid")
    capture = os.environ.get("AGENCY_CAPTURE_CONTENT", "").strip().lower()
    if capture and capture not in {"0", "1", "false", "true", "no", "yes", "off", "on"}:
        raise ConfigValidationError(
            "AGENCY_CAPTURE_CONTENT: environment override is invalid"
        )

    overrides: dict[str, str] = {}
    for variable, path in _ENV_OVERRIDE_PATHS:
        if os.environ.get(variable, ""):
            overrides[path] = variable
    # LITELLM_API_KEY is also the legacy judge fallback when no judge key is
    # otherwise configured.  The hint intentionally reports no secret value.
    if os.environ.get("LITELLM_API_KEY", "") and not os.environ.get(
        "AGENCY_JUDGE_API_KEY", ""
    ):
        overrides.setdefault("judge.api_key", "LITELLM_API_KEY")
    return overrides


def _effective_document(path: Path) -> dict[str, Any]:
    try:
        cfg = load_config(path=path, reload=True)
        rendered = yaml.safe_load(config_to_yaml(cfg, redact=True)) or {}
    except Exception as exc:
        # Loader exceptions may contain submitted scalar text, so expose only a
        # fixed message at this boundary.
        raise ConfigValidationError("configuration could not be loaded") from exc
    if not isinstance(rendered, dict):
        raise ConfigValidationError("effective configuration is invalid")
    try:
        return _redact(validate_config_document(rendered))
    except ConfigValidationError as exc:
        raise ConfigValidationError(
            "effective configuration contains an invalid override"
        ) from exc


def _state_from_document(
    path: Path, document: dict[str, Any], raw: bytes
) -> ConfigState:
    # Validate raw environment inputs before loading applies or silently ignores
    # them, so every reported override is both active and well-typed.
    overrides = _environment_overrides()
    return ConfigState(
        path=str(path),
        persisted=_redact(copy.deepcopy(document)),
        effective=_effective_document(path),
        revision=_revision(raw),
        secret_presence=_secret_presence(document),
        environment_overrides=overrides,
    )


def read_config_state(path: str | Path | None = None) -> ConfigState:
    """Read a consistent, fully redacted persisted/effective config snapshot."""

    target = resolve_config_path(path)
    # Reads remain side-effect-free: an absent config must not create its parent
    # directory or lock file. Atomic replacement guarantees each individual
    # read is complete; a bounded revision check catches a concurrent writer
    # between the persisted and effective snapshots.
    for _attempt in range(3):
        document, raw = _read_document(target)
        validate_config_document(document)
        state = _state_from_document(target, document, raw)
        _latest_document, latest_raw = _read_document(target)
        if raw == latest_raw:
            return state
    raise ConfigConflictError("configuration changed while it was being read; retry")


def _error(path: str, message: str) -> ConfigValidationError:
    return ConfigValidationError(f"{path}: {message}")


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(path, "must be a mapping")
    return value


def _string(
    value: Any,
    path: str,
    *,
    allow_empty: bool = True,
    maximum: int = 4096,
) -> str:
    if not isinstance(value, str):
        raise _error(path, "must be a string")
    if "\x00" in value or len(value) > maximum:
        raise _error(path, "contains invalid text")
    if not allow_empty and not value.strip():
        raise _error(path, "must not be empty")
    return value.strip() if not allow_empty else value


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise _error(path, "must be a JSON boolean")
    return value


def _integer(value: Any, path: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(path, "must be an integer")
    if not minimum <= value <= maximum:
        raise _error(path, "is outside the supported range")
    return value


def _number(value: Any, path: str, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error(path, "must be a number")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise _error(path, "is outside the supported range")
    return result


def _choice(value: Any, path: str, choices: frozenset[str]) -> str:
    result = _string(value, path, allow_empty=False, maximum=80).strip().lower()
    if result not in choices:
        raise _error(path, "has an unsupported value")
    return result


def _env_name(value: Any, path: str) -> str:
    result = _string(value, path, maximum=256).strip()
    if result and _ENV_NAME.fullmatch(result) is None:
        raise _error(path, "must be an environment-variable name")
    return result


def _url(value: Any, path: str, *, allow_empty: bool = False) -> str:
    result = _string(value, path, allow_empty=allow_empty, maximum=2048).strip()
    if not result and allow_empty:
        return ""
    try:
        parsed = urlsplit(result)
        _ = parsed.port
    except ValueError as exc:
        raise _error(path, "must be a valid HTTP(S) URL") from exc
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or any(character.isspace() for character in result)
    ):
        raise _error(path, "must be an uncredentialed HTTP(S) URL")
    return result


def _loopback_host(value: Any, path: str) -> str:
    result = _string(value, path, allow_empty=False, maximum=255).strip().lower()
    if result == "localhost":
        return result
    try:
        if ipaddress.ip_address(result).is_loopback:
            return result
    except ValueError:
        pass
    raise _error(path, "must be a loopback host")


def _enabled(value: Any, path: str) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return _choice(value, path, _ENABLED_VALUES)


def _string_list(
    value: Any,
    path: str,
    *,
    maximum_items: int = 128,
    item_maximum: int = 256,
) -> list[str]:
    if not isinstance(value, list):
        raise _error(path, "must be a list")
    if len(value) > maximum_items:
        raise _error(path, "contains too many items")
    return [
        _string(item, f"{path}.{index}", allow_empty=False, maximum=item_maximum)
        for index, item in enumerate(value)
    ]


def _validate_provider(value: Any, index: int) -> dict[str, Any]:
    path = f"providers.{index}"
    entry = _mapping(value, path)
    allowed = {
        "name",
        "type",
        "model",
        "base_url",
        "api_key",
        "api_key_env",
        "ollama_mode",
        "timeout",
    }
    if set(entry) - allowed:
        raise _error(path, "contains unsupported fields")
    provider_type = _choice(
        entry.get("type", "openai-compatible"), f"{path}.type", _PROVIDER_TYPES
    )
    result: dict[str, Any] = {
        "name": _string(
            entry.get("name", ""), f"{path}.name", allow_empty=False, maximum=80
        ),
        "type": provider_type,
        "model": _string(
            entry.get("model", ""), f"{path}.model", allow_empty=False, maximum=512
        ),
        "base_url": _url(entry.get("base_url", ""), f"{path}.base_url"),
        "api_key": _string(entry.get("api_key", ""), f"{path}.api_key", maximum=65536),
        "api_key_env": _env_name(entry.get("api_key_env", ""), f"{path}.api_key_env"),
        "ollama_mode": _boolean(
            entry.get("ollama_mode", provider_type == "ollama"),
            f"{path}.ollama_mode",
        ),
        "timeout": _number(
            entry.get("timeout", 15.0), f"{path}.timeout", minimum=0.05, maximum=60.0
        ),
    }
    if provider_type == "ollama":
        result["ollama_mode"] = True
    elif not result["api_key"] and not result["api_key_env"]:
        raise _error(path, "requires configured authentication")
    return result


def _validate_providers(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise _error("providers", "must be a list")
    if len(value) > 32:
        raise _error("providers", "contains too many entries")
    providers = [_validate_provider(item, index) for index, item in enumerate(value)]
    names = [provider["name"].casefold() for provider in providers]
    if len(names) != len(set(names)):
        raise _error("providers", "provider names must be unique")
    return providers


def _validate_judge(value: Any) -> dict[str, Any]:
    path = "judge"
    section = _mapping(value, path)
    allowed = {
        "model",
        "base_url",
        "api_key_env",
        "api_key",
        "ollama_mode",
        "timeout",
        "max_selected",
        "confidence_bypass_threshold",
    }
    if set(section) - allowed:
        raise _error(path, "contains unsupported fields")
    validators = {
        "model": lambda item: _string(item, "judge.model", maximum=512),
        "base_url": lambda item: _url(item, "judge.base_url", allow_empty=True),
        "api_key_env": lambda item: _env_name(item, "judge.api_key_env"),
        "api_key": lambda item: _string(item, "judge.api_key", maximum=65536),
        "ollama_mode": lambda item: _boolean(item, "judge.ollama_mode"),
        "timeout": lambda item: _number(
            item, "judge.timeout", minimum=0.05, maximum=60.0
        ),
        "max_selected": lambda item: _integer(
            item, "judge.max_selected", minimum=1, maximum=50
        ),
        "confidence_bypass_threshold": lambda item: _number(
            item,
            "judge.confidence_bypass_threshold",
            minimum=0.0,
            maximum=100.0,
        ),
    }
    return {name: validators[name](item) for name, item in section.items()}


def _validate_ollama(value: Any) -> dict[str, Any]:
    section = _mapping(value, "ollama")
    allowed = {"enabled", "base_url", "model"}
    if set(section) - allowed:
        raise _error("ollama", "contains unsupported fields")
    validators = {
        "enabled": lambda item: _boolean(item, "ollama.enabled"),
        "base_url": lambda item: _url(item, "ollama.base_url"),
        "model": lambda item: _string(
            item, "ollama.model", allow_empty=False, maximum=512
        ),
    }
    return {name: validators[name](item) for name, item in section.items()}


def _validate_selector(value: Any) -> dict[str, Any]:
    section = _mapping(value, "selector")
    allowed = {"min_confidence", "max_user_msg_len", "trivial_msg_threshold"}
    if set(section) - allowed:
        raise _error("selector", "contains unsupported fields")
    validators = {
        "min_confidence": lambda item: _number(
            item, "selector.min_confidence", minimum=0.0, maximum=1.0
        ),
        "max_user_msg_len": lambda item: _integer(
            item, "selector.max_user_msg_len", minimum=1, maximum=1_000_000
        ),
        "trivial_msg_threshold": lambda item: _integer(
            item, "selector.trivial_msg_threshold", minimum=0, maximum=10_000
        ),
    }
    return {name: validators[name](item) for name, item in section.items()}


def _validate_store(value: Any) -> dict[str, Any]:
    section = _mapping(value, "store")
    if set(section) - {"db_path"}:
        raise _error("store", "contains unsupported fields")
    return {
        name: _string(item, "store.db_path", allow_empty=False, maximum=4096)
        for name, item in section.items()
    }


def _validate_server(value: Any) -> dict[str, Any]:
    section = _mapping(value, "server")
    allowed = {"host", "port", "max_body_size"}
    if set(section) - allowed:
        raise _error("server", "contains unsupported fields")
    validators = {
        "host": lambda item: _loopback_host(item, "server.host"),
        "port": lambda item: _integer(item, "server.port", minimum=1, maximum=65535),
        "max_body_size": lambda item: _integer(
            item, "server.max_body_size", minimum=1024, maximum=64 * 1024 * 1024
        ),
    }
    return {name: validators[name](item) for name, item in section.items()}


def _validate_dashboard(value: Any) -> dict[str, Any]:
    section = _mapping(value, "dashboard")
    if set(section) - {"port"}:
        raise _error("dashboard", "contains unsupported fields")
    return {
        name: _integer(item, "dashboard.port", minimum=1, maximum=65535)
        for name, item in section.items()
    }


def _validate_observability(value: Any) -> dict[str, Any]:
    section = _mapping(value, "observability")
    allowed = {"capture_content", "retention_days"}
    if set(section) - allowed:
        raise _error("observability", "contains unsupported fields")
    validators = {
        "capture_content": lambda item: _boolean(item, "observability.capture_content"),
        "retention_days": lambda item: _integer(
            item, "observability.retention_days", minimum=1, maximum=3650
        ),
    }
    return {name: validators[name](item) for name, item in section.items()}


def _validate_adapter_entry(value: Any, name: str) -> dict[str, Any]:
    path = f"adapters.{name}"
    entry = _mapping(value, path)
    allowed = {"enabled"}
    if name == "litellm":
        allowed |= {"base_url", "api_key", "api_key_env", "skip_models"}
    if set(entry) - allowed:
        raise _error(path, "contains unsupported fields")
    result: dict[str, Any] = {}
    for field, item in entry.items():
        item_path = f"{path}.{field}"
        if field == "enabled":
            result[field] = _enabled(item, item_path)
        elif field == "base_url":
            result[field] = _url(item, item_path)
        elif field == "api_key":
            result[field] = _string(item, item_path, maximum=65536)
        elif field == "api_key_env":
            result[field] = _env_name(item, item_path)
        elif field == "skip_models":
            result[field] = _string_list(item, item_path)
    return result


def _validate_adapters(value: Any) -> dict[str, Any]:
    section = _mapping(value, "adapters")
    allowed = {"litellm", "hermes", "openclaw", "codex", "claude"}
    if set(section) - allowed:
        raise _error("adapters", "contains unsupported fields")
    return {name: _validate_adapter_entry(item, name) for name, item in section.items()}


_TOP_LEVEL_VALIDATORS = {
    "providers": _validate_providers,
    "judge": _validate_judge,
    "ollama": _validate_ollama,
    "selector": _validate_selector,
    "store": _validate_store,
    "server": _validate_server,
    "dashboard": _validate_dashboard,
    "observability": _validate_observability,
    "adapters": _validate_adapters,
    "profile": lambda item: _choice(item, "profile", _PROFILES),
    "companion_policy_path": lambda item: (
        None
        if item is None
        else _string(item, "companion_policy_path", allow_empty=False, maximum=4096)
    ),
}


def validate_config_document(document: Mapping[str, Any]) -> dict[str, Any]:
    """Strictly validate a partial persisted configuration document.

    Bundled defaults fill omitted sections during normal loading, so this
    validator requires correct types for present values but does not require a
    fully expanded document.
    """

    if not isinstance(document, Mapping):
        raise ConfigValidationError("configuration root must be a mapping")
    if set(document) - set(_TOP_LEVEL_VALIDATORS):
        raise ConfigValidationError(
            "configuration contains unsupported top-level fields"
        )
    return {
        name: _TOP_LEVEL_VALIDATORS[name](copy.deepcopy(value))
        for name, value in document.items()
    }


def _set_validator(path: str, value: Any) -> Any:
    validators = {
        "profile": lambda item: _choice(item, "profile", _PROFILES),
        "providers": _providers_for_operation,
        "judge.model": lambda item: _string(item, "judge.model", maximum=512),
        "judge.base_url": lambda item: _url(item, "judge.base_url", allow_empty=True),
        "judge.api_key_env": lambda item: _env_name(item, "judge.api_key_env"),
        "judge.ollama_mode": lambda item: _boolean(item, "judge.ollama_mode"),
        "judge.timeout": lambda item: _number(
            item, "judge.timeout", minimum=0.05, maximum=60.0
        ),
        "judge.max_selected": lambda item: _integer(
            item, "judge.max_selected", minimum=1, maximum=50
        ),
        "judge.confidence_bypass_threshold": lambda item: _number(
            item, "judge.confidence_bypass_threshold", minimum=0.0, maximum=100.0
        ),
        "ollama.enabled": lambda item: _boolean(item, "ollama.enabled"),
        "ollama.base_url": lambda item: _url(item, "ollama.base_url"),
        "ollama.model": lambda item: _string(
            item, "ollama.model", allow_empty=False, maximum=512
        ),
        "selector.min_confidence": lambda item: _number(
            item, "selector.min_confidence", minimum=0.0, maximum=1.0
        ),
        "selector.max_user_msg_len": lambda item: _integer(
            item, "selector.max_user_msg_len", minimum=1, maximum=1_000_000
        ),
        "selector.trivial_msg_threshold": lambda item: _integer(
            item, "selector.trivial_msg_threshold", minimum=0, maximum=10_000
        ),
        "store.db_path": lambda item: _string(
            item, "store.db_path", allow_empty=False, maximum=4096
        ),
        "server.host": lambda item: _loopback_host(item, "server.host"),
        "server.port": lambda item: _integer(
            item, "server.port", minimum=1, maximum=65535
        ),
        "server.max_body_size": lambda item: _integer(
            item, "server.max_body_size", minimum=1024, maximum=64 * 1024 * 1024
        ),
        "dashboard.port": lambda item: _integer(
            item, "dashboard.port", minimum=1, maximum=65535
        ),
        "observability.capture_content": lambda item: _boolean(
            item, "observability.capture_content"
        ),
        "observability.retention_days": lambda item: _integer(
            item, "observability.retention_days", minimum=1, maximum=3650
        ),
        "adapters.litellm.enabled": lambda item: _enabled(
            item, "adapters.litellm.enabled"
        ),
        "adapters.litellm.base_url": lambda item: _url(
            item, "adapters.litellm.base_url"
        ),
        "adapters.litellm.api_key_env": lambda item: _env_name(
            item, "adapters.litellm.api_key_env"
        ),
        "adapters.litellm.skip_models": lambda item: _string_list(
            item, "adapters.litellm.skip_models"
        ),
        "adapters.hermes.enabled": lambda item: _enabled(
            item, "adapters.hermes.enabled"
        ),
        "adapters.openclaw.enabled": lambda item: _enabled(
            item, "adapters.openclaw.enabled"
        ),
        "adapters.codex.enabled": lambda item: _enabled(item, "adapters.codex.enabled"),
        "adapters.claude.enabled": lambda item: _enabled(
            item, "adapters.claude.enabled"
        ),
        "companion_policy_path": lambda item: (
            None
            if item is None
            else _string(item, "companion_policy_path", allow_empty=False, maximum=4096)
        ),
    }
    validator = validators.get(path)
    if validator is None:
        raise ConfigValidationError("operation path is not supported")
    return validator(value)


def _providers_for_operation(value: Any) -> list[dict[str, Any]]:
    """Validate a provider list while prohibiting inline direct credentials."""

    if not isinstance(value, list):
        raise _error("providers", "must be a list")
    scrubbed: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise _error(f"providers.{index}", "must be a mapping")
        if "api_key" in item:
            raise _error(f"providers.{index}.api_key", "must use a secret operation")
        scrubbed.append(dict(item))
    # Authentication may be supplied by a preserved secret after this function
    # returns, so use placeholder values solely for structural validation.
    candidates = copy.deepcopy(scrubbed)
    for item in candidates:
        if item.get("type", "openai-compatible") != "ollama" and not item.get(
            "api_key_env"
        ):
            item["api_key"] = "validation-placeholder"
    _validate_providers(candidates)
    return scrubbed


def _nested_set(document: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    target = document
    for part in parts[:-1]:
        current = target.get(part)
        if current is None:
            current = {}
            target[part] = current
        if not isinstance(current, dict):
            raise ConfigValidationError(
                "operation conflicts with the existing configuration shape"
            )
        target = current
    target[parts[-1]] = value


def _apply_provider_list(
    document: dict[str, Any], providers: list[dict[str, Any]]
) -> None:
    existing = document.get("providers")
    secrets_by_name: dict[str, str] = {}
    if isinstance(existing, list):
        for provider in existing:
            if (
                isinstance(provider, dict)
                and provider.get("name")
                and provider.get("api_key")
            ):
                secrets_by_name[str(provider["name"]).casefold()] = str(
                    provider["api_key"]
                )
    result = copy.deepcopy(providers)
    for provider in result:
        secret = secrets_by_name.get(str(provider.get("name", "")).casefold(), "")
        if secret:
            provider["api_key"] = secret
    document["providers"] = result


def _secret_target(document: dict[str, Any], path: str) -> tuple[dict[str, Any], str]:
    if path == "judge.api_key":
        section = document.setdefault("judge", {})
        if not isinstance(section, dict):
            raise ConfigValidationError(
                "secret operation conflicts with the existing configuration shape"
            )
        return section, "api_key"
    if path == "adapters.litellm.api_key":
        adapters = document.setdefault("adapters", {})
        if not isinstance(adapters, dict):
            raise ConfigValidationError(
                "secret operation conflicts with the existing configuration shape"
            )
        section = adapters.setdefault("litellm", {})
        if not isinstance(section, dict):
            raise ConfigValidationError(
                "secret operation conflicts with the existing configuration shape"
            )
        return section, "api_key"
    parts = path.split(".")
    if len(parts) == 3 and parts[0] == "providers" and parts[2] == "api_key":
        try:
            index = int(parts[1])
        except ValueError as exc:
            raise ConfigValidationError(
                "secret operation path is not supported"
            ) from exc
        providers = document.get("providers")
        if not isinstance(providers, list) or not 0 <= index < len(providers):
            raise ConfigValidationError("provider secret target does not exist")
        entry = providers[index]
        if not isinstance(entry, dict):
            raise ConfigValidationError("provider secret target is invalid")
        return entry, "api_key"
    raise ConfigValidationError("secret operation path is not supported")


def _apply_secret_operation(
    document: dict[str, Any], operation: Mapping[str, Any]
) -> str:
    path = operation.get("path")
    action = operation.get("action")
    if not isinstance(path, str) or len(path) > 256:
        raise ConfigValidationError("secret operation path is invalid")
    if action not in {"preserve", "replace", "clear"}:
        raise ConfigValidationError("secret operation action is invalid")
    allowed = {"op", "path", "action"} | ({"value"} if action == "replace" else set())
    if set(operation) - allowed:
        raise ConfigValidationError("secret operation contains unsupported fields")
    target, key = _secret_target(document, path)
    if action == "preserve":
        return path
    if action == "clear":
        target[key] = ""
        return path
    value = operation.get("value")
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 65536
        or value == _REDACTED
    ):
        raise ConfigValidationError("replacement credential is invalid")
    target[key] = value
    return path


def _is_loopback_url(value: Any) -> bool:
    try:
        parsed = urlsplit(str(value))
        hostname = parsed.hostname
        if parsed.scheme not in {"http", "https"} or not hostname:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        if hostname.rstrip(".").lower() == "localhost":
            return True
        return ipaddress.ip_address(hostname).is_loopback
    except (TypeError, ValueError):
        return False


def _enforce_local_only(document: dict[str, Any]) -> bool:
    if str(document.get("profile", "standard")).strip().lower() != "local-only":
        return False
    before = copy.deepcopy(document)
    ollama = document.setdefault("ollama", {})
    if not isinstance(ollama, dict):
        ollama = {}
        document["ollama"] = ollama
    base_url = ollama.get("base_url", "http://127.0.0.1:11434")
    if not _is_loopback_url(base_url):
        base_url = "http://127.0.0.1:11434"
    judge = document.setdefault("judge", {})
    if not isinstance(judge, dict):
        judge = {}
        document["judge"] = judge
    judge_model = (
        judge.get("model", "") if _is_loopback_url(judge.get("base_url", "")) else ""
    )
    model = str(ollama.get("model") or judge_model or "qwen3.5:2b")
    judge.update(
        {
            "model": model,
            "base_url": base_url,
            "api_key": "",
            "api_key_env": "",
            "ollama_mode": True,
        }
    )
    ollama.update({"enabled": True, "base_url": base_url, "model": model})
    document["providers"] = [
        {
            "name": "ollama",
            "type": "ollama",
            "model": model,
            "base_url": base_url,
            "api_key": "",
            "api_key_env": "",
            "ollama_mode": True,
            "timeout": float(judge.get("timeout", 15.0)),
        }
    ]
    adapters = document.setdefault("adapters", {})
    if not isinstance(adapters, dict):
        adapters = {}
        document["adapters"] = adapters
    for name in ("litellm", "hermes", "openclaw", "codex", "claude"):
        entry = adapters.setdefault(name, {})
        if not isinstance(entry, dict):
            entry = {}
            adapters[name] = entry
        entry["enabled"] = "false"
    return document != before


def _changed_restart_paths(changed: set[str]) -> tuple[str, ...]:
    return tuple(
        path
        for path in _RESTART_REQUIRED_PATHS
        if any(
            item == path or item.startswith(f"{path}.") or path.startswith(f"{item}.")
            for item in changed
        )
    )


def _diff_paths(before: Any, after: Any, prefix: str = "") -> set[str]:
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        changed: set[str] = set()
        for key in set(before) | set(after):
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                changed.add(child)
            else:
                changed.update(_diff_paths(before[key], after[key], child))
        return changed
    if before != after:
        return {prefix or "configuration"}
    return set()


def _complete_update(
    target: Path,
    *,
    original: dict[str, Any],
    original_raw: bytes,
    document: dict[str, Any],
    changed: set[str],
    policy_enforced: bool,
    force_write: bool = False,
) -> ConfigUpdateResult:
    if document == original and not force_write:
        changed.clear()
        saved_document = original
        saved_raw = original_raw
    else:
        _atomic_write_yaml(target, document)
        reset_config_cache()
        saved_document, saved_raw = _read_document(target)
    state = _state_from_document(target, saved_document, saved_raw)
    return ConfigUpdateResult(
        state=state,
        changed_paths=tuple(sorted(changed)),
        restart_required=_changed_restart_paths(changed),
        policy_enforced=policy_enforced,
    )


def apply_config_operations(
    operations: Sequence[Mapping[str, Any]],
    *,
    expected_revision: str,
    path: str | Path | None = None,
) -> ConfigUpdateResult:
    """Apply a typed operation batch as one locked, atomic transaction."""

    if isinstance(operations, (str, bytes)) or not isinstance(operations, Sequence):
        raise ConfigValidationError("operations must be a list")
    if not operations or len(operations) > _MAX_OPERATIONS:
        raise ConfigValidationError("operations list has an unsupported size")
    if not isinstance(expected_revision, str) or not expected_revision.startswith(
        "sha256:"
    ):
        raise ConfigValidationError("expected revision is invalid")

    target = resolve_config_path(path)
    with _config_lock(target):
        document, raw = _read_document(target)
        if _revision(raw) != expected_revision:
            raise ConfigConflictError("configuration changed; refresh before saving")
        # Existing invalid documents are never partially repaired by an
        # unrelated operation.  A future migration API can make that explicit.
        document = validate_config_document(document)
        original = copy.deepcopy(document)
        changed: set[str] = set()
        for operation in operations:
            if not isinstance(operation, Mapping):
                raise ConfigValidationError("each operation must be a mapping")
            kind = operation.get("op")
            if kind == "set":
                if set(operation) != {"op", "path", "value"}:
                    raise ConfigValidationError(
                        "set operation contains unsupported fields"
                    )
                operation_path = operation.get("path")
                if not isinstance(operation_path, str) or len(operation_path) > 256:
                    raise ConfigValidationError("set operation path is invalid")
                value = _set_validator(operation_path, operation.get("value"))
                if operation_path == "providers":
                    _apply_provider_list(document, value)
                else:
                    _nested_set(document, operation_path, value)
                changed.add(operation_path)
            elif kind == "secret":
                changed.add(_apply_secret_operation(document, operation))
            else:
                raise ConfigValidationError("operation type is not supported")

        policy_enforced = _enforce_local_only(document)
        if policy_enforced:
            changed.update({"profile", "judge", "ollama", "providers", "adapters"})
        document = validate_config_document(document)
        return _complete_update(
            target,
            original=original,
            original_raw=raw,
            document=document,
            changed=changed,
            policy_enforced=policy_enforced,
        )


def replace_config_document(
    document: Mapping[str, Any],
    *,
    expected_revision: str,
    path: str | Path | None = None,
    recover_invalid_existing: bool = False,
) -> ConfigUpdateResult:
    """Replace the persisted document through the same safe transaction path.

    This entry point is intended for the guided CLI configurator. Dashboard
    callers should prefer operation batches so omitted secrets are preserved.
    ``recover_invalid_existing`` is reserved for the CLI's explicit ``--force``
    recovery path; revision checking and locking remain mandatory. The returned
    state remains redacted even when the trusted input contains credentials.
    """

    if not isinstance(document, Mapping):
        raise ConfigValidationError("configuration root must be a mapping")
    if not isinstance(expected_revision, str) or not expected_revision.startswith(
        "sha256:"
    ):
        raise ConfigValidationError("expected revision is invalid")

    target = resolve_config_path(path)
    with _config_lock(target):
        raw = _read_raw(target)
        if _revision(raw) != expected_revision:
            raise ConfigConflictError("configuration changed; refresh before saving")
        recovered = False
        try:
            original = validate_config_document(_parse_document(raw))
        except ConfigValidationError:
            if not recover_invalid_existing:
                raise
            original = {}
            recovered = True
        replacement = validate_config_document(copy.deepcopy(document))
        policy_enforced = _enforce_local_only(replacement)
        replacement = validate_config_document(replacement)
        changed = _diff_paths(original, replacement)
        return _complete_update(
            target,
            original=original,
            original_raw=raw,
            document=replacement,
            changed=changed,
            policy_enforced=policy_enforced,
            force_write=recovered,
        )


def _restrict_windows_acl(path: Path) -> bool:
    """Apply an owner-only Windows DACL using native APIs when available."""

    if not _IS_WINDOWS:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class TrusteeW(ctypes.Structure):
            _fields_ = [
                ("pMultipleTrustee", ctypes.c_void_p),
                ("MultipleTrusteeOperation", wintypes.DWORD),
                ("TrusteeForm", wintypes.DWORD),
                ("TrusteeType", wintypes.DWORD),
                ("ptstrName", wintypes.LPWSTR),
            ]

        class ExplicitAccessW(ctypes.Structure):
            _fields_ = [
                ("grfAccessPermissions", wintypes.DWORD),
                ("grfAccessMode", wintypes.DWORD),
                ("grfInheritance", wintypes.DWORD),
                ("Trustee", TrusteeW),
            ]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_security = advapi32.GetNamedSecurityInfoW
        get_security.argtypes = [
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        get_security.restype = wintypes.DWORD
        set_entries = advapi32.SetEntriesInAclW
        set_entries.argtypes = [
            wintypes.ULONG,
            ctypes.POINTER(ExplicitAccessW),
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        set_entries.restype = wintypes.DWORD
        set_security = advapi32.SetNamedSecurityInfoW
        set_security.argtypes = [
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        set_security.restype = wintypes.DWORD
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        owner_sid = ctypes.c_void_p()
        descriptor = ctypes.c_void_p()
        acl = ctypes.c_void_p()
        try:
            code = get_security(
                str(path),
                1,  # SE_FILE_OBJECT
                0x00000001,  # OWNER_SECURITY_INFORMATION
                ctypes.byref(owner_sid),
                None,
                None,
                None,
                ctypes.byref(descriptor),
            )
            if code:
                return False
            trustee = TrusteeW(
                None,
                0,
                0,  # TRUSTEE_IS_SID
                1,  # TRUSTEE_IS_USER
                ctypes.cast(owner_sid, wintypes.LPWSTR),
            )
            access = ExplicitAccessW(
                0x001F01FF,  # FILE_ALL_ACCESS
                2,  # SET_ACCESS
                0,
                trustee,
            )
            code = set_entries(1, ctypes.byref(access), None, ctypes.byref(acl))
            if code:
                return False
            code = set_security(
                str(path),
                1,
                0x00000004 | 0x80000000,  # DACL + protected DACL
                None,
                None,
                acl,
                None,
            )
            return code == 0
        finally:
            if acl:
                kernel32.LocalFree(acl)
            if descriptor:
                kernel32.LocalFree(descriptor)
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return False


def _restrict_permissions(path: Path, *, required: bool = False) -> bool:
    if _IS_WINDOWS:
        try:
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
        except OSError:
            pass
        restricted = _restrict_windows_acl(path)
        if required and not restricted:
            raise ConfigurationError(
                "owner-only file permissions could not be enforced"
            )
        return restricted
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return True


def restrict_private_file(path: str | Path) -> None:
    """Apply the same owner-only file policy used by configuration writes."""

    _restrict_permissions(Path(path), required=True)


def _preflight_effective_candidate(path: Path) -> None:
    """Validate the exact secured candidate with active environment overlays."""

    reset_config_cache()
    try:
        _environment_overrides()
        _effective_document(path)
    finally:
        # Keep a failed preflight from poisoning later readers, and ensure a
        # successful replacement is reloaded from its final path.
        reset_config_cache()


def _atomic_write_yaml(path: Path, document: Mapping[str, Any]) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not _IS_WINDOWS:
        try:
            os.chmod(path.parent, stat.S_IRWXU)
        except OSError:
            pass
    payload = yaml.safe_dump(
        dict(document),
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    encoded = payload.encode("utf-8")
    if len(encoded) > _MAX_CONFIG_BYTES:
        raise ConfigValidationError("configuration exceeds the size limit")
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        # mkstemp inherits its parent DACL on Windows. Harden the still-empty
        # file before any credential bytes can be written.
        _restrict_permissions(temporary, required=True)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            fd = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        # Reassert/verify the policy after the write and before validation and
        # replacement. The secured temporary file retains its descriptor when
        # moved within the same directory.
        _restrict_permissions(temporary, required=True)
        _preflight_effective_candidate(temporary)
        os.replace(temporary, path)
        if not _IS_WINDOWS:
            _restrict_permissions(path, required=True)
            try:
                directory_fd = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                pass
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def _config_lock(
    path: Path, *, timeout: float = _LOCK_TIMEOUT_SECONDS
) -> Iterator[None]:
    """Acquire a cooperative one-byte lock adjacent to the config file."""

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = path.with_name(f".{path.name}.lock")
    handle = open(lock_path, "a+b")
    try:
        if lock_path.stat().st_size == 0:
            handle.write(b"\0")
            handle.flush()
        # Lock files contain no credentials; inability to narrow their ACL must
        # not prevent a secure config file from being written.
        _restrict_permissions(lock_path)
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            try:
                handle.seek(0)
                if _IS_WINDOWS:
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise ConfigLockError(
                        "configuration is busy; retry the operation"
                    ) from exc
                time.sleep(0.025)
        try:
            yield
        finally:
            handle.seek(0)
            if _IS_WINDOWS:
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


__all__ = [
    "ConfigConflictError",
    "ConfigLockError",
    "ConfigState",
    "ConfigUpdateResult",
    "ConfigValidationError",
    "ConfigurationError",
    "apply_config_operations",
    "read_config_revision",
    "read_config_state",
    "replace_config_document",
    "restrict_private_file",
    "resolve_config_path",
    "validate_config_document",
]
