"""Shared provider validation for guided configuration and doctor checks."""

from __future__ import annotations

import math
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from numbers import Real
from typing import Any
from urllib.parse import urlsplit

from agency_runtime.core.cli_transport import CLIProviderStatus, inspect_cli_transport
from agency_runtime.core.config import (
    ProviderEntry,
    _is_loopback_http_url,
    is_safe_credential_url,
)
from agency_runtime.core.http_safety import open_no_redirect


@dataclass(frozen=True, slots=True)
class ProviderValidationResult:
    name: str
    provider_type: str
    ok: bool
    usable: bool
    reason: str = ""
    installed: bool | None = None
    authenticated: bool | None = None


def _join_api_path(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    normalized_path = "/" + path.lstrip("/")
    if base.lower().endswith("/v1") and normalized_path.lower().startswith("/v1/"):
        normalized_path = normalized_path[3:]
    return f"{base}{normalized_path}"


def _is_http_endpoint(value: str) -> bool:
    """Validate the URL shape before constructing or dispatching a probe."""

    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except (TypeError, ValueError):
        return False
    return bool(
        parsed.scheme.casefold() in {"http", "https"}
        and parsed.hostname
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
        and not any(character.isspace() for character in value)
    )


def _cli_result(
    provider: ProviderEntry,
    inspector: Callable[..., CLIProviderStatus],
    timeout: float,
) -> ProviderValidationResult:
    status = inspector(provider.transport, timeout=timeout)
    return ProviderValidationResult(
        name=provider.name,
        provider_type="cli",
        ok=status.usable,
        usable=status.usable,
        reason=status.reason,
        installed=status.installed,
        authenticated=status.authenticated,
    )


def validate_provider(
    provider: ProviderEntry,
    *,
    timeout: float = 5.0,
    opener: Callable[..., Any] | None = None,
    cli_inspector: Callable[..., CLIProviderStatus] = inspect_cli_transport,
) -> ProviderValidationResult:
    """Validate one configured entry without returning endpoint or credential data."""

    provider_type = provider.type.strip().lower()
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, Real)
        or not math.isfinite(float(timeout))
        or float(timeout) <= 0
    ):
        return ProviderValidationResult(
            provider.name,
            provider_type,
            False,
            False,
            "validation timeout is invalid",
        )
    if provider_type == "cli":
        return _cli_result(provider, cli_inspector, timeout)
    if not provider.model or not provider.base_url:
        return ProviderValidationResult(
            provider.name,
            provider_type,
            False,
            False,
            "model and base URL are required",
        )
    if not _is_http_endpoint(provider.base_url):
        return ProviderValidationResult(
            provider.name,
            provider_type,
            False,
            False,
            "base URL must be an uncredentialed HTTP(S) endpoint",
        )
    api_key = provider.resolve_api_key()
    if api_key and not is_safe_credential_url(provider.base_url):
        return ProviderValidationResult(
            provider.name,
            provider_type,
            False,
            False,
            "credentials require HTTPS or literal loopback HTTP",
            authenticated=False,
        )
    keyless_loopback = provider_type in {
        "openai",
        "openai-compatible",
        "litellm",
    } and _is_loopback_http_url(provider.base_url)
    if not (provider_type == "ollama" or provider.ollama_mode or api_key or keyless_loopback):
        return ProviderValidationResult(
            provider.name,
            provider_type,
            False,
            False,
            "configured authentication is unavailable",
            authenticated=False,
        )

    path = "/api/tags" if provider_type == "ollama" or provider.ollama_mode else "/v1/models"
    headers: dict[str, str] = {}
    if api_key:
        if provider_type == "anthropic":
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }
        else:
            headers = {"Authorization": f"Bearer {api_key}"}
    request = urllib.request.Request(
        _join_api_path(provider.base_url, path),
        headers=headers,
    )
    request_opener = opener or open_no_redirect
    try:
        with request_opener(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 0))
            ok = status == 200
    except Exception as exc:
        return ProviderValidationResult(
            provider.name,
            provider_type,
            False,
            False,
            f"network probe failed ({type(exc).__name__})",
            authenticated=None,
        )
    authenticated: bool | None = None
    if api_key:
        if ok:
            authenticated = True
        elif status in {401, 403}:
            authenticated = False
    return ProviderValidationResult(
        provider.name,
        provider_type,
        ok,
        ok,
        "" if ok else "provider returned a non-success status",
        authenticated=authenticated,
    )


__all__ = ["ProviderValidationResult", "validate_provider"]
