"""Health diagnostics for `agency doctor`.

Checks every subsystem and returns a structured report.
"""

from __future__ import annotations

import json
import re
import sqlite3
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from agency_runtime.core.config import AgencyConfig, ProviderEntry, load_config
from agency_runtime.core.installer import inspect_host_installations
from agency_runtime.core.policy.profiles import PROFILES


_MAX_HTTP_JSON_BYTES = 1024 * 1024
_MAX_DIAGNOSTIC_CHARS = 500
_MAX_DIAGNOSTIC_MODELS = 1000
_URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)


def _safe_endpoint(value: str) -> str:
    """Render an endpoint without credentials, query parameters, or fragments."""
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if not parsed.scheme or not host:
            return "<invalid endpoint>"
        rendered_host = f"[{host}]" if ":" in host else host
        if parsed.port is not None:
            rendered_host = f"{rendered_host}:{parsed.port}"
        return urlunsplit((parsed.scheme, rendered_host, "", "", ""))
    except (TypeError, ValueError):
        return "<invalid endpoint>"


def _sanitize_diagnostic(value: Any, *, secrets: tuple[str, ...] = ()) -> str:
    """Bound diagnostic text and remove common credential-bearing URL parts."""
    text = str(value)
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted>")
    text = _URL_PATTERN.sub(lambda match: _safe_endpoint(match.group(0)), text)
    text = " ".join(text.split())
    return text[:_MAX_DIAGNOSTIC_CHARS]


def _join_api_path(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    normalized_path = "/" + path.lstrip("/")
    if base.lower().endswith("/v1") and normalized_path.lower().startswith("/v1/"):
        normalized_path = normalized_path[3:]
    return f"{base}{normalized_path}"


@dataclass
class CheckResult:
    name: str
    status: str  # "pass", "warn", "fail"
    message: str = ""
    detail: str = ""


@dataclass
class DoctorReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        has_fail = any(c.status == "fail" for c in self.checks)
        has_warn = any(c.status == "warn" for c in self.checks)
        if has_fail:
            return 1
        if has_warn:
            return 2
        return 0

    @property
    def overall_status(self) -> str:
        if any(c.status == "fail" for c in self.checks):
            return "FAILED"
        if any(c.status == "warn" for c in self.checks):
            return "DEGRADED"
        return "HEALTHY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.overall_status,
            "exit_code": self.exit_code,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "message": _sanitize_diagnostic(c.message),
                    "detail": _sanitize_diagnostic(c.detail),
                }
                for c in self.checks
            ],
        }


def _http_check(url: str, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200, f"HTTP {resp.status}"
    except Exception as exc:
        return False, f"network error ({type(exc).__name__})"


def _http_check_authed(
    url: str,
    api_key: str,
    timeout: float = 2.0,
    *,
    provider_type: str = "openai-compatible",
) -> tuple[bool, str]:
    """HTTP check with Authorization header for authenticated endpoints."""
    try:
        if provider_type.strip().lower() == "anthropic":
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }
        else:
            headers = {"Authorization": f"Bearer {api_key}"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200, f"HTTP {resp.status}"
    except Exception as exc:
        return False, f"network error ({type(exc).__name__})"


def _http_get_json(url: str, timeout: float = 2.0) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(_MAX_HTTP_JSON_BYTES + 1)
        if len(raw) > _MAX_HTTP_JSON_BYTES:
            return None
        parsed = json.loads(raw.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _probe_provider(provider: ProviderEntry, *, timeout: float = 5.0) -> tuple[bool, str]:
    """Probe a configured provider using its declared wire protocol."""
    provider_type = provider.type.strip().lower()
    if provider_type == "ollama" or provider.ollama_mode:
        return _http_check(_join_api_path(provider.base_url, "/api/tags"), timeout)

    api_key = provider.resolve_api_key()
    models_url = _join_api_path(provider.base_url, "/v1/models")
    if api_key:
        return _http_check_authed(
            models_url,
            api_key,
            timeout,
            provider_type=provider_type,
        )
    return _http_check(models_url, timeout)


def _provider_is_ready(provider: ProviderEntry) -> bool:
    """Mirror the selector's minimum requirements for a network attempt."""
    if not provider.model or not provider.base_url:
        return False
    return (
        provider.type.strip().lower() == "ollama"
        or provider.ollama_mode
        or bool(provider.resolve_api_key())
    )


def run_doctor(config: AgencyConfig | None = None) -> DoctorReport:
    """Run all health checks and return a structured report."""
    cfg = config or load_config()
    report = DoctorReport()

    # ── Config checks ─────────────────────────────────────────
    if cfg.config_path and Path(cfg.config_path).exists():
        report.checks.append(CheckResult("config_file", "pass", f"Config file: {cfg.config_path}"))
    else:
        report.checks.append(CheckResult("config_file", "warn", "No config file found — using bundled defaults"))

    if cfg.profile in PROFILES:
        report.checks.append(CheckResult("config_profile", "pass", f"Profile: {cfg.profile}"))
    else:
        report.checks.append(CheckResult("config_profile", "fail", f"Unknown profile: {cfg.profile}"))

    # ── Database checks ───────────────────────────────────────
    db_path = cfg.store.resolved_path()
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            version = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            count_row = conn.execute("SELECT COUNT(*) FROM agent_active").fetchone()
        finally:
            conn.close()

        if integrity and integrity[0] == "ok":
            report.checks.append(CheckResult("db_integrity", "pass", f"SQLite integrity OK: {db_path}"))
        else:
            report.checks.append(CheckResult("db_integrity", "fail", f"SQLite integrity check failed: {integrity}"))

        if version:
            report.checks.append(CheckResult("db_schema", "pass", f"Schema version: {version[0]}"))
        else:
            report.checks.append(CheckResult("db_schema", "fail", "Schema version table empty"))

        roster_count = count_row[0] if count_row else 0
        if roster_count > 0:
            report.checks.append(CheckResult("db_roster", "pass", f"Roster: {roster_count} agents active"))
        else:
            report.checks.append(CheckResult("db_roster", "fail", "No active agents — run `agency install`"))

    except Exception as exc:
        report.checks.append(CheckResult("db", "fail", f"Database error: {exc}", str(exc)))

    # ── Judge / selector checks ───────────────────────────────
    primary_provider = next(
        (provider for provider in cfg.providers if _provider_is_ready(provider)),
        None,
    )
    api_key = cfg.judge.resolve_api_key()

    if primary_provider is not None:
        provider_type = primary_provider.type.strip().lower()
        if provider_type != "ollama":
            source = (
                "stored in config"
                if primary_provider.api_key
                else f"from ${primary_provider.api_key_env}"
            )
            report.checks.append(CheckResult(
                "judge_api_key",
                "pass",
                f"API key present ({_sanitize_diagnostic(source)})",
            ))
        ok, msg = _probe_provider(primary_provider, timeout=5)
        endpoint = _safe_endpoint(primary_provider.base_url)
        if ok:
            report.checks.append(CheckResult(
                "judge_provider",
                "pass",
                f"Judge provider {provider_type} reachable at {endpoint}",
            ))
        else:
            report.checks.append(CheckResult(
                "judge_provider",
                "fail",
                f"Judge provider {provider_type} unreachable at {endpoint}: {msg}",
            ))
    elif (not cfg.judge.ollama_mode) and bool(api_key):
        source = (
            "stored in config"
            if cfg.judge.api_key
            else f"from ${cfg.judge.api_key_env}"
        )
        report.checks.append(CheckResult(
            "judge_api_key",
            "pass",
            f"API key present ({_sanitize_diagnostic(source)})",
        ))
        models_url = _join_api_path(cfg.judge.base_url, "/v1/models")
        ok, msg = _http_check_authed(models_url, api_key, timeout=5)
        endpoint = _safe_endpoint(cfg.judge.base_url)
        report.checks.append(CheckResult(
            "judge_provider",
            "pass" if ok else "fail",
            (
                f"Judge endpoint reachable: {endpoint}"
                if ok
                else f"Judge endpoint unreachable: {endpoint}: {msg}"
            ),
        ))
    elif cfg.judge.ollama_mode or (not api_key and cfg.ollama.enabled):
        if cfg.ollama.enabled:
            tags_url = _join_api_path(cfg.ollama.base_url, "/api/tags")
            ok, msg = _http_check(tags_url, timeout=5)
            endpoint = _safe_endpoint(cfg.ollama.base_url)
            if ok:
                report.checks.append(CheckResult("judge_provider", "pass",
                    f"Ollama reachable at {endpoint}"))
                tags = _http_get_json(tags_url)
                if tags:
                    entries = tags.get("models", [])
                    models = [
                        str(item.get("name", ""))[:200]
                        for item in (
                            entries[:_MAX_DIAGNOSTIC_MODELS]
                            if isinstance(entries, list)
                            else []
                        )
                        if isinstance(item, dict) and item.get("name")
                    ]
                    if cfg.judge.model in models:
                        report.checks.append(CheckResult("judge_model", "pass",
                            f"Judge model '{cfg.judge.model}' available"))
                    else:
                        report.checks.append(CheckResult(
                            "judge_model",
                            "warn",
                            f"Judge model '{cfg.judge.model}' not in {len(models)} reported Ollama models",
                        ))
            else:
                report.checks.append(CheckResult("judge_provider", "fail",
                    f"Ollama unreachable at {endpoint}: {msg}"))
        else:
            report.checks.append(CheckResult("judge_provider", "warn", "Ollama disabled, no provider configured"))
    else:
        report.checks.append(CheckResult("judge_provider", "warn",
            "No judge provider configured — run `agency configure`"))

    report.checks.append(CheckResult("judge_threshold", "pass",
        f"Confidence bypass threshold: {cfg.judge.confidence_bypass_threshold}"))

    # ── Adapter checks ────────────────────────────────────────
    def check_adapter(
        name: str,
        enabled: str,
        detected: bool,
        installation: dict[str, Any] | None = None,
    ):
        if enabled == "false":
            report.checks.append(CheckResult(f"adapter_{name}", "pass",
                f"{name}: disabled (skipping)"))
            return

        if name == "litellm":
            if enabled == "true" or (enabled == "auto" and detected):
                endpoint = _safe_endpoint(cfg.adapters.litellm.base_url)
                # Health check (unauthenticated)
                ok, msg = _http_check(
                    _join_api_path(cfg.adapters.litellm.base_url, "/health/liveness"),
                    timeout=3,
                )
                if ok:
                    # Verify auth works with configured key
                    adapter_key = cfg.adapters.litellm.resolve_api_key()
                    if adapter_key:
                        auth_ok, auth_msg = _http_check_authed(
                            _join_api_path(cfg.adapters.litellm.base_url, "/v1/models"),
                            adapter_key,
                            timeout=3,
                        )
                        if auth_ok:
                            report.checks.append(CheckResult("adapter_litellm", "pass",
                                f"LiteLLM reachable + authenticated: {endpoint}"))
                        else:
                            report.checks.append(CheckResult("adapter_litellm", "warn",
                                f"LiteLLM reachable but models endpoint failed (auth?): {auth_msg}"))
                    else:
                        report.checks.append(CheckResult("adapter_litellm", "pass",
                            f"LiteLLM reachable (no key configured): {endpoint}"))
                else:
                    status = "warn" if enabled == "auto" else "fail"
                    report.checks.append(CheckResult("adapter_litellm", status,
                        f"LiteLLM unreachable: {endpoint}: {msg}"))
            else:
                report.checks.append(CheckResult("adapter_litellm", "pass",
                    "LiteLLM: not detected (skipping)"))
            return

        host = installation or {}
        if host.get("stale_config"):
            status = "fail" if enabled == "true" else "warn"
            report.checks.append(CheckResult(
                f"adapter_{name}",
                status,
                f"{name}: stale config root without a current host executable/state marker",
                str(host.get("native_root") or ""),
            ))
        elif not detected:
            if enabled == "true":
                report.checks.append(CheckResult(f"adapter_{name}", "fail",
                    f"{name}: enabled in config but not found"))
            else:
                report.checks.append(CheckResult(f"adapter_{name}", "pass",
                    f"{name}: not installed (auto-skip)"))
        elif not host.get("registered"):
            status = "fail" if enabled == "true" else "warn"
            report.checks.append(CheckResult(
                f"adapter_{name}",
                status,
                f"{name}: host discovered but Agency Runtime is not natively registered",
                f"maturity={host.get('maturity', 'host-discovered')}",
            ))
        elif host.get("enabled") is False:
            status = "fail" if enabled == "true" else "warn"
            report.checks.append(CheckResult(
                f"adapter_{name}",
                status,
                f"{name}: Agency Runtime is registered but disabled",
            ))
        elif host.get("loaded") is False:
            report.checks.append(CheckResult(
                f"adapter_{name}",
                "fail",
                f"{name}: Agency Runtime is enabled but native runtime inspection did not load it",
            ))
        elif host.get("loaded") is True:
            report.checks.append(CheckResult(
                f"adapter_{name}",
                "pass",
                f"{name}: Agency Runtime native plugin loaded and verified",
            ))
        elif host.get("enabled") is True:
            report.checks.append(CheckResult(
                f"adapter_{name}",
                "warn",
                f"{name}: Agency Runtime enabled; live runtime loading is not provable from cold inventory",
                f"maturity={host.get('maturity', 'enabled-runtime-unverified')}",
            ))
        else:
            report.checks.append(CheckResult(
                f"adapter_{name}",
                "warn",
                f"{name}: Agency Runtime registered; enablement is not provable from native inventory",
                f"maturity={host.get('maturity', 'registered-enablement-unverified')}",
            ))

    # Detect adapters
    litellm_ok, _ = _http_check(
        _join_api_path(cfg.adapters.litellm.base_url, "/health/liveness"),
        timeout=2,
    )
    host_installations = {
        item["host"]: item
        for item in inspect_host_installations(probe_runtime=False)
    }
    check_adapter("litellm", cfg.adapters.litellm.enabled, litellm_ok)
    check_adapter("hermes", cfg.adapters.hermes.enabled,
        bool(host_installations.get("hermes", {}).get("discovered")), host_installations.get("hermes"))
    check_adapter("openclaw", cfg.adapters.openclaw.enabled,
        bool(host_installations.get("openclaw", {}).get("discovered")), host_installations.get("openclaw"))
    check_adapter("codex", cfg.adapters.codex.enabled,
        bool(host_installations.get("codex", {}).get("discovered")), host_installations.get("codex"))
    check_adapter("claude", cfg.adapters.claude.enabled,
        bool(host_installations.get("claude", {}).get("discovered")), host_installations.get("claude"))

    # ── Provider fallback chain checks ─────────────────────────
    if cfg.providers:
        available_count = 0
        for provider in cfg.providers:
            auth = provider.auth_method()
            if _provider_is_ready(provider):
                available_count += 1
                report.checks.append(CheckResult(
                    f"provider_{provider.name}", "pass",
                    f"{provider.name}: {provider.type} model={provider.model} auth={auth}",
                ))
            elif not provider.model or not provider.base_url:
                report.checks.append(CheckResult(
                    f"provider_{provider.name}", "warn",
                    f"{provider.name}: incomplete provider configuration (model and base_url required)",
                ))
            else:
                report.checks.append(CheckResult(
                    f"provider_{provider.name}", "warn",
                    f"{provider.name}: configured but no API key (need {provider.api_key_env or 'api_key'})",
                ))

        if available_count == 0:
            report.checks.append(CheckResult("provider_chain", "fail",
                "No providers in fallback chain are available — judge will use token-only"))
        else:
            chain_names = " → ".join(p.name for p in cfg.providers)
            report.checks.append(CheckResult("provider_chain", "pass",
                f"Fallback chain ({available_count} available): {chain_names}"))
    else:
        report.checks.append(CheckResult("provider_chain", "warn",
            "No providers list configured — using legacy judge/ollama fallback. Run `agency configure`."))

    return report


def format_report_human(report: DoctorReport) -> str:
    """Format a doctor report for human reading."""
    lines = [
        "",
        "  Agency Runtime Health Check",
        "  ═══════════════════════════",
        "",
    ]

    icons = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}

    for check in report.checks:
        icon = icons.get(check.status, "?")
        lines.append(f"  {icon} {check.name}: {_sanitize_diagnostic(check.message)}")

    lines.append("")
    lines.append("  ─────────────────────────")

    if report.overall_status == "HEALTHY":
        lines.append("  Result: ✅ HEALTHY — all checks passed")
    elif report.overall_status == "DEGRADED":
        lines.append("  Result: ⚠️  DEGRADED — selector works, some features unavailable")
    else:
        lines.append("  Result: ❌ FAILED — some critical checks failed")

    lines.append("")
    return "\n".join(lines)
