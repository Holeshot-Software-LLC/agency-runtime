"""Shared, side-effect-free helpers for Agency Runtime CLI commands."""

from __future__ import annotations

import ipaddress
import json
import sys
from collections.abc import Sequence
from dataclasses import fields, is_dataclass
from typing import Any
from urllib.parse import urlsplit

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.store.sqlite import Store

REDACTED = "***REDACTED***"
SECRET_KEY_PARTS = {
    "api_key",
    "access_token",
    "auth_token",
    "client_secret",
    "password",
    "refresh_token",
    "secret",
    "token",
}


def store(config: AgencyConfig | None = None) -> Store:
    """Open the configured store, or the environment-selected default store."""
    if config:
        config_path = getattr(config, "config_path", "") or None
        if config_path is None:
            return Store(config.store.resolved_path())
        return Store(
            config.store.resolved_path(),
            config_path=config_path,
        )
    return Store()


def print_json(data: Any) -> None:
    """Emit stable, human-readable JSON for command results."""
    print(json.dumps(data, indent=2, sort_keys=True))


def configure_console_output() -> None:
    """Keep human CLI output usable on legacy Windows console encodings."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            # Captured, detached, and application-owned streams may reject
            # reconfiguration. Those streams retain their existing behavior.
            continue


def is_secret_config_part(part: str) -> bool:
    normalized = part.strip().lower().replace("-", "_")
    if normalized.endswith("_env"):
        return False
    return normalized in SECRET_KEY_PARTS or any(
        normalized.endswith(f"_{secret}") for secret in SECRET_KEY_PARTS
    )


def config_display_value(
    value: Any,
    *,
    path: tuple[str, ...] = (),
    raw: bool = False,
) -> Any:
    """Convert config objects to JSON-safe values and recursively redact."""
    if not raw and path and is_secret_config_part(path[-1]):
        return REDACTED if value not in (None, "") else value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: config_display_value(
                getattr(value, item.name),
                path=(*path, item.name),
                raw=raw,
            )
            for item in fields(value)
        }
    if isinstance(value, dict):
        return {
            str(key): config_display_value(
                nested,
                path=(*path, str(key)),
                raw=raw,
            )
            for key, nested in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [
            config_display_value(nested, path=(*path, str(index)), raw=raw)
            for index, nested in enumerate(value)
        ]
    return value


def format_config_value(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)) or (
        is_dataclass(value) and not isinstance(value, type)
    ):
        return json.dumps(config_display_value(value, raw=True), sort_keys=True)
    return str(value)


def nested_config_value(data: Any, parts: Sequence[str]) -> Any:
    """Read a path from the raw YAML shape after policy enforcement."""
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, (list, tuple)):
            current = current[int(part)]
        else:
            raise KeyError(".".join(parts))
    return current


def is_loopback_url(value: Any) -> bool:
    try:
        hostname = urlsplit(str(value)).hostname
        if not hostname:
            return False
        if hostname.lower() == "localhost":
            return True
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def enforce_local_only_config(data: dict[str, Any]) -> dict[str, Any]:
    """Make the local-only profile a write-time, no-remote invariant."""
    if str(data.get("profile", "standard")).strip().lower() != "local-only":
        return data

    ollama = data.get("ollama")
    if not isinstance(ollama, dict):
        ollama = {}
        data["ollama"] = ollama
    base_url = ollama.get("base_url", "http://127.0.0.1:11434")
    if not is_loopback_url(base_url):
        base_url = "http://127.0.0.1:11434"

    raw_providers = data.get("providers")
    local_providers: list[dict[str, Any]] = []
    if isinstance(raw_providers, list):
        for raw_provider in raw_providers:
            if not isinstance(raw_provider, dict):
                continue
            provider_type = str(raw_provider.get("type", "openai-compatible")).strip().lower()
            provider_base = raw_provider.get("base_url", "")
            if provider_type not in {
                "ollama",
                "openai",
                "openai-compatible",
                "litellm",
            } or not is_loopback_url(provider_base):
                continue
            provider = dict(raw_provider)
            provider["api_key"] = ""
            provider["api_key_env"] = ""
            provider["transport"] = ""
            provider["ollama_mode"] = provider_type == "ollama"
            local_providers.append(provider)

    judge = data.get("judge")
    if not isinstance(judge, dict):
        judge = {}
    judge_base = judge.get("base_url", "")
    judge_model = judge.get("model", "") if is_loopback_url(judge_base) else ""
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
    data["judge"] = judge
    ollama.update({"enabled": True, "base_url": base_url, "model": model})
    data["providers"] = local_providers

    adapters = data.get("adapters")
    if not isinstance(adapters, dict):
        adapters = {}
        data["adapters"] = adapters
    for name in ("litellm", "hermes", "openclaw", "codex", "claude", "zcode"):
        entry = adapters.get(name)
        if not isinstance(entry, dict):
            entry = {}
            adapters[name] = entry
        entry["enabled"] = "false"
    return data
