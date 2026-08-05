"""Typed schema and field registry for persisted configuration documents."""

from __future__ import annotations

import copy
import ipaddress
import math
import re
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit

from agency_runtime.core.agent_activation import normalize_disabled_agents
from agency_runtime.core.config import (
    CODEX_REASONING_EFFORTS,
    INFERENCE_ADAPTER_TYPES,
    INFERENCE_CAPABILITY_CLASSES,
    INFERENCE_PROFILE_NAME_PATTERN,
    INFERENCE_ROUTE_KEY_PATTERN,
    INFERENCE_THINKING_LEVELS,
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
_DELEGATION_MODES = frozenset({"observe", "prefer", "strong"})
_WORKFORCE_MODES = frozenset({"fast", "balanced", "strict"})


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
        "reasoning_effort",
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
            entry.get("timeout", 15.0), f"{path}.timeout", minimum=0.05, maximum=120.0
        ),
        "reasoning_effort": _string(
            entry.get("reasoning_effort", ""),
            f"{path}.reasoning_effort",
            maximum=16,
        )
        .strip()
        .lower(),
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
        if result["reasoning_effort"] and (
            result["transport"] != "codex"
            or result["reasoning_effort"] not in CODEX_REASONING_EFFORTS
        ):
            raise _error(
                f"{path}.reasoning_effort",
                "is supported only for Codex CLI providers and must be one of "
                + ", ".join(sorted(CODEX_REASONING_EFFORTS)),
            )
        result["ollama_mode"] = False
    else:
        result["transport"] = _string(transport_value, f"{path}.transport", maximum=80).strip()
        if result["transport"]:
            raise _error(path, "transport is supported only for CLI providers")
        if result["reasoning_effort"]:
            raise _error(path, "reasoning_effort is supported only for Codex CLI providers")
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


def _validate_delegation(value: Any) -> dict[str, Any]:
    section = _mapping(value, "delegation")
    allowed = {
        "mode",
        "preferred_min_units",
        "strongly_preferred_min_units",
        "strongly_preferred_min_confidence",
        "child_inference_budget",
        "child_inference_concurrency",
        "child_cache_ttl_seconds",
    }
    if set(section) - allowed:
        raise _error("delegation", "contains unsupported fields")
    validators: dict[str, Callable[[Any], Any]] = {
        "mode": lambda item: _choice(item, "delegation.mode", _DELEGATION_MODES),
        "preferred_min_units": lambda item: _integer(
            item, "delegation.preferred_min_units", minimum=2, maximum=16
        ),
        "strongly_preferred_min_units": lambda item: _integer(
            item,
            "delegation.strongly_preferred_min_units",
            minimum=2,
            maximum=16,
        ),
        "strongly_preferred_min_confidence": lambda item: _number(
            item,
            "delegation.strongly_preferred_min_confidence",
            minimum=0.0,
            maximum=1.0,
        ),
        "child_inference_budget": lambda item: _integer(
            item, "delegation.child_inference_budget", minimum=0, maximum=256
        ),
        "child_inference_concurrency": lambda item: _integer(
            item, "delegation.child_inference_concurrency", minimum=1, maximum=32
        ),
        "child_cache_ttl_seconds": lambda item: _integer(
            item, "delegation.child_cache_ttl_seconds", minimum=0, maximum=86400
        ),
    }
    result = {name: validators[name](item) for name, item in section.items()}
    preferred = result.get("preferred_min_units")
    strongly_preferred = result.get("strongly_preferred_min_units")
    if preferred is not None and strongly_preferred is not None and strongly_preferred < preferred:
        raise _error(
            "delegation.strongly_preferred_min_units",
            "must be greater than or equal to preferred_min_units",
        )
    return result


def _validate_workforce(value: Any) -> dict[str, Any]:
    section = _mapping(value, "workforce")
    allowed = {
        "mode",
        "provider",
        "fast_call_budget",
        "balanced_call_budget",
        "strict_call_budget",
        "hiring_call_budget",
        "max_work_units",
        "max_selected_per_unit",
        "max_selected_total",
        "min_confidence",
        "min_margin",
        "max_hires_per_task",
        "max_hires_per_day",
        "max_hires_per_turn",
        "daily_hire_alert_threshold",
        "auto_promote_successes",
        "contractor_review_days",
        "hiring_repair_budget",
        "amend_overlap_threshold",
    }
    if set(section) - allowed:
        raise _error("workforce", "contains unsupported fields")
    validators: dict[str, Callable[[Any], Any]] = {
        "mode": lambda item: _choice(item, "workforce.mode", _WORKFORCE_MODES),
        "provider": lambda item: _string(item, "workforce.provider", maximum=80).strip(),
        "fast_call_budget": lambda item: _integer(
            item, "workforce.fast_call_budget", minimum=1, maximum=8
        ),
        "balanced_call_budget": lambda item: _integer(
            item, "workforce.balanced_call_budget", minimum=1, maximum=8
        ),
        "strict_call_budget": lambda item: _integer(
            item, "workforce.strict_call_budget", minimum=1, maximum=8
        ),
        "hiring_call_budget": lambda item: _integer(
            item, "workforce.hiring_call_budget", minimum=1, maximum=8
        ),
        "max_work_units": lambda item: _integer(
            item, "workforce.max_work_units", minimum=1, maximum=64
        ),
        "max_selected_per_unit": lambda item: _integer(
            item, "workforce.max_selected_per_unit", minimum=1, maximum=16
        ),
        "max_selected_total": lambda item: _integer(
            item, "workforce.max_selected_total", minimum=1, maximum=256
        ),
        "min_confidence": lambda item: _number(
            item, "workforce.min_confidence", minimum=0.0, maximum=1.0
        ),
        "min_margin": lambda item: _number(item, "workforce.min_margin", minimum=0.0, maximum=1.0),
        "max_hires_per_task": lambda item: _integer(
            item, "workforce.max_hires_per_task", minimum=0, maximum=16
        ),
        "max_hires_per_day": lambda item: _integer(
            item, "workforce.max_hires_per_day", minimum=0, maximum=100
        ),
        "max_hires_per_turn": lambda item: _integer(
            item, "workforce.max_hires_per_turn", minimum=1, maximum=256
        ),
        "daily_hire_alert_threshold": lambda item: _integer(
            item, "workforce.daily_hire_alert_threshold", minimum=0, maximum=10_000
        ),
        "auto_promote_successes": lambda item: _integer(
            item, "workforce.auto_promote_successes", minimum=0, maximum=10_000
        ),
        "contractor_review_days": lambda item: _integer(
            item, "workforce.contractor_review_days", minimum=1, maximum=3650
        ),
        "hiring_repair_budget": lambda item: _integer(
            item, "workforce.hiring_repair_budget", minimum=0, maximum=8
        ),
        "amend_overlap_threshold": lambda item: _number(
            item, "workforce.amend_overlap_threshold", minimum=0.0, maximum=1.0
        ),
    }
    result = {name: validators[name](item) for name, item in section.items()}
    balanced = result.get("balanced_call_budget", 4)
    # A partial persisted document may carry an explicit legacy balanced cap
    # while omitting fast. Preserve that operator-owned cap instead of making a
    # fresh default bump invalidate a previously valid document.
    fast = result.get("fast_call_budget", min(4, balanced))
    strict = result.get("strict_call_budget", 5)
    if fast > balanced:
        raise _error(
            "workforce.balanced_call_budget", "must be greater than or equal to fast_call_budget"
        )
    if balanced > strict:
        raise _error(
            "workforce.strict_call_budget", "must be greater than or equal to balanced_call_budget"
        )
    per_unit = result.get("max_selected_per_unit", 4)
    total = result.get("max_selected_total", 16)
    if per_unit > total:
        raise _error(
            "workforce.max_selected_total", "must be greater than or equal to max_selected_per_unit"
        )
    if has_terminal_control(result.get("provider", "")):
        raise _error("workforce.provider", "contains terminal control characters")
    return result


def _validate_agents(value: Any) -> dict[str, Any]:
    section = _mapping(value, "agents")
    if set(section) - {"disabled"}:
        raise _error("agents", "contains unsupported fields")
    try:
        disabled = normalize_disabled_agents(section.get("disabled", []))
    except ValueError as exc:
        raise _error("agents.disabled", str(exc)) from exc
    return {"disabled": list(disabled)}


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
    allowed = {"litellm", "hermes", "openclaw", "codex", "claude", "zcode"}
    if set(section) - allowed:
        raise _error("adapters", "contains unsupported fields")
    return {name: _validate_adapter_entry(item, name) for name, item in section.items()}


def _validate_inference_profile(name: str, value: Any) -> dict[str, Any]:
    path = f"inference.profiles.{name}"
    section = _mapping(value, path)
    if not INFERENCE_PROFILE_NAME_PATTERN.fullmatch(name):
        raise _error(path, "profile names must be lowercase alphanumeric or hyphenated")
    allowed = {
        "adapter",
        "model",
        "thinking_level",
        "capability_class",
        "base_url",
        "api_key",
        "api_key_env",
        "timeout_ms",
    }
    if set(section) - allowed:
        raise _error(path, "contains unsupported fields")
    adapter = _choice(
        section.get("adapter", "openai-compatible"), f"{path}.adapter", INFERENCE_ADAPTER_TYPES
    )
    is_cli = adapter == "cli"
    model = _string(
        section.get("model", ""),
        f"{path}.model",
        allow_empty=is_cli,
        maximum=512,
    )
    if not is_cli and not model:
        raise _error(f"{path}.model", "must be a non-empty model identifier")
    thinking_level = (
        _string(
            section.get("thinking_level", ""),
            f"{path}.thinking_level",
            allow_empty=True,
            maximum=16,
        )
        .strip()
        .casefold()
    )
    if thinking_level and thinking_level not in INFERENCE_THINKING_LEVELS:
        raise _error(
            f"{path}.thinking_level",
            "must be one of " + ", ".join(sorted(INFERENCE_THINKING_LEVELS)),
        )
    capability_class = (
        _string(
            section.get("capability_class", ""),
            f"{path}.capability_class",
            allow_empty=True,
            maximum=32,
        )
        .strip()
        .casefold()
    )
    if capability_class and capability_class not in INFERENCE_CAPABILITY_CLASSES:
        raise _error(
            f"{path}.capability_class",
            "must be one of " + ", ".join(sorted(INFERENCE_CAPABILITY_CLASSES)),
        )
    base_url = _url(
        section.get("base_url", ""),
        f"{path}.base_url",
        allow_empty=is_cli,
    )
    api_key = _string(section.get("api_key", ""), f"{path}.api_key", maximum=65536)
    api_key_env = _env_name(section.get("api_key_env", ""), f"{path}.api_key_env")
    if api_key and api_key_env:
        raise _error(
            path,
            "api_key and api_key_env are mutually exclusive; choose one",
        )
    timeout_ms = _integer(
        section.get("timeout_ms", 30_000),
        f"{path}.timeout_ms",
        minimum=50,
        maximum=120_000,
    )
    if is_cli and (base_url or api_key or api_key_env):
        raise _error(
            path,
            "CLI profiles cannot configure URL or API-key fields",
        )
    if not is_cli and not (api_key or api_key_env) and not base_url:
        raise _error(
            path,
            "non-CLI profiles must declare base_url or credential fields",
        )
    if (api_key or api_key_env) and not is_safe_credential_url(base_url):
        raise _error(
            f"{path}.base_url",
            "credentials require HTTPS or literal loopback HTTP",
        )
    return {
        "adapter": adapter,
        "model": model,
        "thinking_level": thinking_level,
        "capability_class": capability_class,
        "base_url": base_url,
        "api_key": api_key,
        "api_key_env": api_key_env,
        "timeout_ms": timeout_ms,
    }


def _validate_inference(value: Any) -> dict[str, Any]:
    path = "inference"
    section = _mapping(value, path)
    allowed = {"default_profile", "strict_independence", "routes", "profiles"}
    if set(section) - allowed:
        raise _error(path, "contains unsupported fields")
    default_profile = _string(
        section.get("default_profile", ""),
        "inference.default_profile",
        maximum=128,
    ).strip()
    strict_independence = _boolean(
        section.get("strict_independence", False),
        "inference.strict_independence",
    )
    routes_raw = section.get("routes", {})
    routes_section = _mapping(routes_raw, "inference.routes")
    routes: dict[str, str] = {}
    for key, item in routes_section.items():
        if not isinstance(key, str) or not INFERENCE_ROUTE_KEY_PATTERN.fullmatch(key):
            raise _error(
                f"inference.routes.{key!r}",
                "route keys must be lowercase dotted identifiers",
            )
        if not isinstance(item, str) or not item.strip():
            raise _error(f"inference.routes.{key}", "must name a profile")
        routes[key] = item.strip()
    profiles_raw = section.get("profiles", {})
    profiles_section = _mapping(profiles_raw, "inference.profiles")
    profiles: dict[str, dict[str, Any]] = {}
    for name, item in profiles_section.items():
        if not isinstance(name, str) or not name.strip():
            raise _error("inference.profiles", "profile names must be non-empty strings")
        profiles[name] = _validate_inference_profile(name, item)
    if default_profile and default_profile not in profiles:
        raise _error(
            "inference.default_profile",
            f"must reference a profile in inference.profiles (got {default_profile!r})",
        )
    missing = sorted(set(routes.values()) - set(profiles))
    if missing:
        raise _error(
            "inference.routes",
            "routes reference undefined profile(s): " + ", ".join(missing),
        )
    return {
        "default_profile": default_profile,
        "strict_independence": strict_independence,
        "routes": routes,
        "profiles": profiles,
    }


_TOP_LEVEL_VALIDATORS: dict[str, Callable[[Any], Any]] = {
    "providers": _validate_providers,
    "judge": _validate_judge,
    "ollama": _validate_ollama,
    "selector": _validate_selector,
    "delegation": _validate_delegation,
    "workforce": _validate_workforce,
    "inference": _validate_inference,
    "agents": _validate_agents,
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
