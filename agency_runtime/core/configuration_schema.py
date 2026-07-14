"""Typed schema and field registry for persisted configuration documents."""

from __future__ import annotations

import copy
import ipaddress
import math
import re
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit

from agency_runtime.core.config import (
    MAX_PROVIDER_CHAIN_ENTRIES,
    is_safe_cli_model_id,
    is_safe_credential_url,
)
from agency_runtime.core.configuration_contracts import ConfigValidationError
from agency_runtime.core.display import has_terminal_control

_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROVIDER_TYPES = frozenset(
    {"openai", "openai-compatible", "anthropic", "ollama", "litellm", "cli"}
)
_CLI_TRANSPORTS = frozenset({"codex", "claude"})
_PROFILES = frozenset({"local-only", "standard", "power", "yolo"})
_ENABLED_VALUES = frozenset({"auto", "true", "false"})


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
        or parsed.query
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


def _validate_provider(value: Any, index: int) -> dict[str, Any]:
    path = f"providers.{index}"
    entry = _mapping(value, path)
    allowed = {
        "name",
        "type",
        "transport",
        "model",
        "base_url",
        "api_key",
        "api_key_env",
        "ollama_mode",
        "timeout",
    }
    if set(entry) - allowed:
        raise _error(path, "contains unsupported fields")
    provider_type = _choice(entry.get("type", "openai-compatible"), f"{path}.type", _PROVIDER_TYPES)
    is_cli = provider_type == "cli"
    result: dict[str, Any] = {
        "name": _string(entry.get("name", ""), f"{path}.name", allow_empty=False, maximum=80),
        "type": provider_type,
        "model": _string(
            entry.get("model", ""),
            f"{path}.model",
            allow_empty=is_cli,
            maximum=512,
        ),
        "base_url": _url(entry.get("base_url", ""), f"{path}.base_url", allow_empty=is_cli),
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
    for field in ("name", "model"):
        if has_terminal_control(result[field]):
            raise _error(f"{path}.{field}", "contains terminal control characters")
    transport_value = entry.get("transport", "")
    if is_cli:
        result["transport"] = _choice(transport_value, f"{path}.transport", _CLI_TRANSPORTS)
        if not is_safe_cli_model_id(result["model"]):
            raise _error(
                f"{path}.model",
                "must be an empty default or a bounded model identifier",
            )
        if result["base_url"] or result["api_key"] or result["api_key_env"]:
            raise _error(path, "CLI providers cannot configure URL or API-key fields")
        result["ollama_mode"] = False
    else:
        result["transport"] = _string(transport_value, f"{path}.transport", maximum=80).strip()
        if result["transport"]:
            raise _error(path, "transport is supported only for CLI providers")
    if provider_type == "ollama":
        result["ollama_mode"] = True
    elif (
        not is_cli
        and not result["api_key"]
        and not result["api_key_env"]
        and not (
            provider_type in {"openai", "openai-compatible", "litellm"}
            and _is_loopback_url(result["base_url"])
        )
    ):
        raise _error(path, "requires configured authentication")
    if (result["api_key"] or result["api_key_env"]) and not is_safe_credential_url(
        result["base_url"]
    ):
        raise _error(
            f"{path}.base_url",
            "credentials require HTTPS or literal loopback HTTP",
        )
    return result


def _validate_providers(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise _error("providers", "must be a list")
    if len(value) > MAX_PROVIDER_CHAIN_ENTRIES:
        raise _error(
            "providers",
            f"supports at most {MAX_PROVIDER_CHAIN_ENTRIES} entries",
        )
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
    validators: dict[str, Callable[[Any], Any]] = {
        "model": lambda item: _string(item, "judge.model", maximum=512),
        "base_url": lambda item: _url(item, "judge.base_url", allow_empty=True),
        "api_key_env": lambda item: _env_name(item, "judge.api_key_env"),
        "api_key": lambda item: _string(item, "judge.api_key", maximum=65536),
        "ollama_mode": lambda item: _boolean(item, "judge.ollama_mode"),
        "timeout": lambda item: _number(item, "judge.timeout", minimum=0.05, maximum=60.0),
        "max_selected": lambda item: _integer(item, "judge.max_selected", minimum=1, maximum=50),
        "confidence_bypass_threshold": lambda item: _number(
            item,
            "judge.confidence_bypass_threshold",
            minimum=0.0,
            maximum=100.0,
        ),
    }
    result = {name: validators[name](item) for name, item in section.items()}
    if (
        (result.get("api_key") or result.get("api_key_env"))
        and "base_url" in result
        and not is_safe_credential_url(result["base_url"])
    ):
        raise _error(
            "judge.base_url",
            "credentials require HTTPS or literal loopback HTTP",
        )
    return result


def _validate_ollama(value: Any) -> dict[str, Any]:
    section = _mapping(value, "ollama")
    allowed = {"enabled", "base_url", "model"}
    if set(section) - allowed:
        raise _error("ollama", "contains unsupported fields")
    validators: dict[str, Callable[[Any], Any]] = {
        "enabled": lambda item: _boolean(item, "ollama.enabled"),
        "base_url": lambda item: _url(item, "ollama.base_url"),
        "model": lambda item: _string(item, "ollama.model", allow_empty=False, maximum=512),
    }
    return {name: validators[name](item) for name, item in section.items()}


def _validate_selector(value: Any) -> dict[str, Any]:
    section = _mapping(value, "selector")
    allowed = {"min_confidence", "max_user_msg_len", "trivial_msg_threshold"}
    if set(section) - allowed:
        raise _error("selector", "contains unsupported fields")
    validators: dict[str, Callable[[Any], Any]] = {
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
    validators: dict[str, Callable[[Any], Any]] = {
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
    validators: dict[str, Callable[[Any], Any]] = {
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
        else:
            # The section allowlist above makes skip_models the only remaining
            # field after the explicit scalar cases.
            result[field] = _string_list(item, item_path)
    if (
        name == "litellm"
        and (result.get("api_key") or result.get("api_key_env"))
        and "base_url" in result
        and not is_safe_credential_url(result["base_url"])
    ):
        raise _error(
            f"{path}.base_url",
            "credentials require HTTPS or literal loopback HTTP",
        )
    return result


def _validate_adapters(value: Any) -> dict[str, Any]:
    section = _mapping(value, "adapters")
    allowed = {"litellm", "hermes", "openclaw", "codex", "claude"}
    if set(section) - allowed:
        raise _error("adapters", "contains unsupported fields")
    return {name: _validate_adapter_entry(item, name) for name, item in section.items()}


_TOP_LEVEL_VALIDATORS: dict[str, Callable[[Any], Any]] = {
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
    """Strictly validate a partial persisted configuration document."""

    if not isinstance(document, Mapping):
        raise ConfigValidationError("configuration root must be a mapping")
    if set(document) - set(_TOP_LEVEL_VALIDATORS):
        raise ConfigValidationError("configuration contains unsupported top-level fields")
    return {
        name: _TOP_LEVEL_VALIDATORS[name](copy.deepcopy(value)) for name, value in document.items()
    }
