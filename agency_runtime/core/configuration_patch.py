"""Typed operation normalization and policy enforcement for configuration."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from agency_runtime.core.agent_activation import normalize_disabled_agents
from agency_runtime.core.configuration_contracts import (
    MAX_OPERATIONS,
    REDACTED,
    RESTART_REQUIRED_PATHS,
    ConfigValidationError,
)
from agency_runtime.core.configuration_schema import (
    _PROFILES,
    _boolean,
    _choice,
    _enabled,
    _env_name,
    _error,
    _integer,
    _is_loopback_url,
    _loopback_host,
    _number,
    _string,
    _string_list,
    _url,
    _validate_providers,
    validate_config_document,
)


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
    # returns, so placeholders are used solely for structural validation.
    candidates = copy.deepcopy(scrubbed)
    for item in candidates:
        provider_type = item.get("type", "openai-compatible")
        if (
            provider_type not in {"ollama", "cli"}
            and not item.get("api_key_env")
            and not (
                provider_type in {"openai", "openai-compatible", "litellm"}
                and _is_loopback_url(item.get("base_url", ""))
            )
        ):
            item["api_key"] = "validation-placeholder"
    _validate_providers(candidates)
    return scrubbed


_SET_VALIDATORS = {
    "profile": lambda item: _choice(item, "profile", _PROFILES),
    "providers": _providers_for_operation,
    "judge.model": lambda item: _string(item, "judge.model", maximum=512),
    "judge.base_url": lambda item: _url(item, "judge.base_url", allow_empty=True),
    "judge.api_key_env": lambda item: _env_name(item, "judge.api_key_env"),
    "judge.ollama_mode": lambda item: _boolean(item, "judge.ollama_mode"),
    "judge.timeout": lambda item: _number(item, "judge.timeout", minimum=0.05, maximum=60.0),
    "judge.max_selected": lambda item: _integer(item, "judge.max_selected", minimum=1, maximum=50),
    "judge.confidence_bypass_threshold": lambda item: _number(
        item,
        "judge.confidence_bypass_threshold",
        minimum=0.0,
        maximum=100.0,
    ),
    "ollama.enabled": lambda item: _boolean(item, "ollama.enabled"),
    "ollama.base_url": lambda item: _url(item, "ollama.base_url"),
    "ollama.model": lambda item: _string(item, "ollama.model", allow_empty=False, maximum=512),
    "selector.min_confidence": lambda item: _number(
        item, "selector.min_confidence", minimum=0.0, maximum=1.0
    ),
    "selector.max_user_msg_len": lambda item: _integer(
        item, "selector.max_user_msg_len", minimum=1, maximum=1_000_000
    ),
    "selector.trivial_msg_threshold": lambda item: _integer(
        item, "selector.trivial_msg_threshold", minimum=0, maximum=10_000
    ),
    "delegation.mode": lambda item: _choice(
        item,
        "delegation.mode",
        frozenset({"observe", "prefer", "strong"}),
    ),
    "delegation.preferred_min_units": lambda item: _integer(
        item, "delegation.preferred_min_units", minimum=2, maximum=16
    ),
    "delegation.strongly_preferred_min_units": lambda item: _integer(
        item,
        "delegation.strongly_preferred_min_units",
        minimum=2,
        maximum=16,
    ),
    "delegation.strongly_preferred_min_confidence": lambda item: _number(
        item,
        "delegation.strongly_preferred_min_confidence",
        minimum=0.0,
        maximum=1.0,
    ),
    "agents.disabled": lambda item: list(normalize_disabled_agents(item)),
    "store.db_path": lambda item: _string(item, "store.db_path", allow_empty=False, maximum=4096),
    "server.host": lambda item: _loopback_host(item, "server.host"),
    "server.port": lambda item: _integer(item, "server.port", minimum=1, maximum=65535),
    "server.max_body_size": lambda item: _integer(
        item, "server.max_body_size", minimum=1024, maximum=64 * 1024 * 1024
    ),
    "dashboard.port": lambda item: _integer(item, "dashboard.port", minimum=1, maximum=65535),
    "observability.capture_content": lambda item: _boolean(item, "observability.capture_content"),
    "observability.retention_days": lambda item: _integer(
        item, "observability.retention_days", minimum=1, maximum=3650
    ),
    "adapters.litellm.enabled": lambda item: _enabled(item, "adapters.litellm.enabled"),
    "adapters.litellm.base_url": lambda item: _url(item, "adapters.litellm.base_url"),
    "adapters.litellm.api_key_env": lambda item: _env_name(item, "adapters.litellm.api_key_env"),
    "adapters.litellm.skip_models": lambda item: _string_list(item, "adapters.litellm.skip_models"),
    "adapters.hermes.enabled": lambda item: _enabled(item, "adapters.hermes.enabled"),
    "adapters.openclaw.enabled": lambda item: _enabled(item, "adapters.openclaw.enabled"),
    "adapters.codex.enabled": lambda item: _enabled(item, "adapters.codex.enabled"),
    "adapters.claude.enabled": lambda item: _enabled(item, "adapters.claude.enabled"),
    "companion_policy_path": lambda item: (
        None
        if item is None
        else _string(item, "companion_policy_path", allow_empty=False, maximum=4096)
    ),
}


def _set_validator(path: str, value: Any) -> Any:
    validator = _SET_VALIDATORS.get(path)
    if validator is None:
        raise ConfigValidationError("operation path is not supported")
    return validator(value)


def _nested_set(document: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    target = document
    for part in parts[:-1]:
        current = target.get(part)
        if current is None:
            current = {}
            target[part] = current
        if not isinstance(current, dict):
            raise ConfigValidationError("operation conflicts with the existing configuration shape")
        target = current
    target[parts[-1]] = value


def _apply_provider_list(document: dict[str, Any], providers: list[dict[str, Any]]) -> None:
    existing = document.get("providers")
    secrets_by_name: dict[str, str] = {}
    if isinstance(existing, list):
        for provider in existing:
            if isinstance(provider, dict) and provider.get("name") and provider.get("api_key"):
                secrets_by_name[str(provider["name"]).casefold()] = str(provider["api_key"])
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
            raise ConfigValidationError("secret operation path is not supported") from exc
        providers = document.get("providers")
        if not isinstance(providers, list) or not 0 <= index < len(providers):
            raise ConfigValidationError("provider secret target does not exist")
        entry = providers[index]
        if not isinstance(entry, dict):
            raise ConfigValidationError("provider secret target is invalid")
        return entry, "api_key"
    raise ConfigValidationError("secret operation path is not supported")


def _apply_secret_operation(document: dict[str, Any], operation: Mapping[str, Any]) -> str:
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
    if not isinstance(value, str) or not value or len(value) > 65536 or value == REDACTED:
        raise ConfigValidationError("replacement credential is invalid")
    target[key] = value
    return path


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
    raw_providers = document.get("providers")
    local_providers: list[dict[str, Any]] = []
    if isinstance(raw_providers, list):
        for raw_provider in raw_providers:
            if not isinstance(raw_provider, dict):
                continue
            provider_type = str(raw_provider.get("type", "openai-compatible")).strip().lower()
            if provider_type not in {
                "ollama",
                "openai",
                "openai-compatible",
                "litellm",
            } or not _is_loopback_url(raw_provider.get("base_url", "")):
                continue
            provider = copy.deepcopy(raw_provider)
            provider.update(
                {
                    "api_key": "",
                    "api_key_env": "",
                    "transport": "",
                    "ollama_mode": provider_type == "ollama",
                }
            )
            local_providers.append(provider)
    judge = document.setdefault("judge", {})
    if not isinstance(judge, dict):
        judge = {}
        document["judge"] = judge
    judge_model = judge.get("model", "") if _is_loopback_url(judge.get("base_url", "")) else ""
    model = str(ollama.get("model") or judge_model or "qwen3.5:2b")
    if not local_providers:
        local_providers = [
            {
                "name": "ollama",
                "type": "ollama",
                "transport": "",
                "model": model,
                "base_url": base_url,
                "api_key": "",
                "api_key_env": "",
                "ollama_mode": True,
                "timeout": float(judge.get("timeout", 15.0)),
            }
        ]
    primary = local_providers[0]
    judge.update(
        {
            "model": str(primary.get("model") or model),
            "base_url": str(primary.get("base_url") or base_url),
            "api_key": "",
            "api_key_env": "",
            "ollama_mode": bool(primary.get("ollama_mode", False)),
        }
    )
    ollama.update({"enabled": True, "base_url": base_url, "model": model})
    document["providers"] = local_providers
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
        for path in RESTART_REQUIRED_PATHS
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


def validate_operation_batch(operations: Sequence[Mapping[str, Any]]) -> None:
    """Validate batch-level limits before entering the write lock."""

    if isinstance(operations, (str, bytes)) or not isinstance(operations, Sequence):
        raise ConfigValidationError("operations must be a list")
    if not operations or len(operations) > MAX_OPERATIONS:
        raise ConfigValidationError("operations list has an unsupported size")


def apply_operations(
    document: dict[str, Any], operations: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], set[str], bool]:
    """Apply a validated operation batch and return its normalized result."""

    changed: set[str] = set()
    for operation in operations:
        if not isinstance(operation, Mapping):
            raise ConfigValidationError("each operation must be a mapping")
        kind = operation.get("op")
        if kind == "set":
            if set(operation) != {"op", "path", "value"}:
                raise ConfigValidationError("set operation contains unsupported fields")
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
    return validate_config_document(document), changed, policy_enforced
