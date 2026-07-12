"""Shared provider validation for guided configuration and doctor checks."""

from __future__ import annotations

import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

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
    keyless_loopback = (
        provider_type in {"openai", "openai-compatible", "litellm"}
        and _is_loopback_http_url(provider.base_url)
    )
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
            ok = int(getattr(response, "status", 0)) == 200
    except Exception as exc:
        return ProviderValidationResult(
            provider.name,
            provider_type,
            False,
            False,
            f"network probe failed ({type(exc).__name__})",
            authenticated=bool(api_key) if not keyless_loopback else None,
        )
    return ProviderValidationResult(
        provider.name,
        provider_type,
        ok,
        ok,
        "" if ok else "provider returned a non-success status",
        authenticated=bool(api_key) if not keyless_loopback else None,
    )


__all__ = ["ProviderValidationResult", "validate_provider"]
