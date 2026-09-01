"""Health diagnostics for `agency doctor`.

Checks every subsystem and returns a structured report.
"""

from __future__ import annotations

import re
import sqlite3
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.config import (
    AgencyConfig,
    ProviderEntry,
    is_safe_credential_url,
    load_config,
)
from agency_runtime.core.display import safe_display_token
from agency_runtime.core.http_safety import open_no_redirect
from agency_runtime.core.installer import inspect_host_installations
from agency_runtime.core.policy.profiles import PROFILES
from agency_runtime.core.provider_validation import (
    ProviderValidationResult,
    validate_provider,
)

_MAX_HTTP_JSON_BYTES = 1024 * 1024
_MAX_DIAGNOSTIC_CHARS = 500
_MAX_DIAGNOSTIC_MODELS = 1000
_URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_PROVIDER_VALIDATION_TIMEOUT_SECONDS = 2.0
_PROVIDER_VALIDATION_WORKERS = 4


def _sanitize_url_match(match: re.Match[str]) -> str:
    """Redact a URL without consuming punctuation from its sentence."""
    candidate = match.group(0)
    suffix = ""
    rendered = _safe_endpoint(candidate)
    while rendered == "<invalid endpoint>" and candidate[-1:] in ".,;:!?)}]":
        suffix = candidate[-1] + suffix
        candidate = candidate[:-1]
        rendered = _safe_endpoint(candidate)
    return rendered + suffix


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
    text = safe_display_token(value, limit=_MAX_DIAGNOSTIC_CHARS * 2)
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted>")
    text = _URL_PATTERN.sub(_sanitize_url_match, text)
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
                    "name": _sanitize_diagnostic(c.name),
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
        with open_no_redirect(req, timeout=timeout) as resp:
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
    if not is_safe_credential_url(url):
        return False, "credential transport requires HTTPS or literal loopback HTTP"
    try:
        if provider_type.strip().lower() == "anthropic":
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }
        else:
            headers = {"Authorization": f"Bearer {api_key}"}
        req = urllib.request.Request(url, headers=headers)
        with open_no_redirect(req, timeout=timeout) as resp:
            return resp.status == 200, f"HTTP {resp.status}"
    except Exception as exc:
        return False, f"network error ({type(exc).__name__})"


def _http_get_json(url: str, timeout: float = 2.0) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url)
        with open_no_redirect(req, timeout=timeout) as resp:
            raw = resp.read(_MAX_HTTP_JSON_BYTES + 1)
        if len(raw) > _MAX_HTTP_JSON_BYTES:
            return None
        parsed = safe_load_bounded_json(
            raw,
            maximum_bytes=_MAX_HTTP_JSON_BYTES,
            maximum_depth=32,
            maximum_nodes=10_000,
        )
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _provider_is_ready(provider: ProviderEntry) -> bool:
    """Return structural readiness; live usability is validated separately."""

    return provider.is_available()


def _validate_provider_entries(
    providers: tuple[ProviderEntry, ...],
) -> list[ProviderValidationResult]:
    """Probe every entry concurrently while preserving configured order."""

    if not providers:
        return []

    def validate(entry: ProviderEntry) -> ProviderValidationResult:
        try:
            return validate_provider(
                entry,
                timeout=min(entry.timeout, _PROVIDER_VALIDATION_TIMEOUT_SECONDS),
                opener=open_no_redirect,
            )
        except Exception:
            return ProviderValidationResult(
                name=entry.name,
                provider_type=entry.type,
                ok=False,
                usable=False,
                reason="provider validation failed unexpectedly",
            )

    with ThreadPoolExecutor(
        max_workers=min(_PROVIDER_VALIDATION_WORKERS, len(providers)),
        thread_name_prefix="agency-provider-check",
    ) as executor:
        return list(executor.map(validate, providers))


ProviderValidations = dict[int, ProviderValidationResult]
HostInstallation = dict[str, Any]


def _config_checks(cfg: AgencyConfig) -> list[CheckResult]:
    if cfg.config_path and Path(cfg.config_path).exists():
        config_file = CheckResult("config_file", "pass", f"Config file: {cfg.config_path}")
    else:
        config_file = CheckResult(
            "config_file", "warn", "No config file found — using bundled defaults"
        )

    profile = CheckResult(
        "config_profile",
        "pass" if cfg.profile in PROFILES else "fail",
        f"Profile: {cfg.profile}" if cfg.profile in PROFILES else f"Unknown profile: {cfg.profile}",
    )
    checks = [config_file, profile]
    # A policy dropped at load time is invisible by design -- the turn still runs.
    # Doctor is where an operator finds out their house rules stopped applying.
    if cfg.operator_policy_error:
        checks.append(
            CheckResult(
                "operator_policy",
                "warn",
                f"Operator policy is not being applied: {cfg.operator_policy_error}",
            )
        )
    elif cfg.operator_policy:
        checks.append(
            CheckResult(
                "operator_policy",
                "pass",
                f"Operator policy: {len(cfg.operator_policy)} characters, applied every turn",
            )
        )
    return checks


def _read_database_state(
    db_path: Path,
) -> tuple[tuple[Any, ...] | None, tuple[Any, ...] | None, tuple[Any, ...] | None]:
    if not db_path.is_file():
        raise FileNotFoundError(f"database does not exist: {db_path}")
    conn = sqlite3.connect(
        db_path.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=2,
    )
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        version = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        count_row = conn.execute("SELECT COUNT(*) FROM agent_active").fetchone()
        return integrity, version, count_row
    finally:
        conn.close()


def _schema_version_check(version: tuple[Any, ...] | None) -> CheckResult:
    """Compare the store's schema against the runtime that is actually running.

    Reporting the stored number alone is how this check passed green on
    2026-08-14 while every hook on the machine was refusing that same store:
    a repository checkout had migrated it to 46 and the pinned launcher the
    hooks run was still 45.  ``Store.__init__`` raises on that, the hook
    boundary fails open, and the operator sees nothing but a missing card.
    ``doctor`` is the one place that drift should be impossible to miss.
    """

    from agency_runtime.core.store.schema import SCHEMA_VERSION

    if not version:
        return CheckResult("db_schema", "fail", "Schema version table empty")
    stored = version[0]
    if not isinstance(stored, int) or isinstance(stored, bool):
        return CheckResult(
            "db_schema",
            "fail",
            f"Schema version is not a number: {stored!r}",
        )
    if stored == SCHEMA_VERSION:
        return CheckResult("db_schema", "pass", f"Schema version: {stored}")
    if stored > SCHEMA_VERSION:
        return CheckResult(
            "db_schema",
            "fail",
            f"Schema version {stored} is newer than this runtime ({SCHEMA_VERSION}); "
            "this runtime refuses the store, so every hook fails open and nothing is "
            "staffed or recorded. Reinstall so the launcher the hooks run matches the "
            "store.",
            f"store={stored} runtime={SCHEMA_VERSION}",
        )
    return CheckResult(
        "db_schema",
        "warn",
        f"Schema version {stored} is older than this runtime ({SCHEMA_VERSION}); "
        "the store migrates on next open, which will refuse any older runtime still "
        "installed elsewhere.",
        f"store={stored} runtime={SCHEMA_VERSION}",
    )


def _database_checks(cfg: AgencyConfig) -> list[CheckResult]:
    db_path = cfg.store.resolved_path()
    try:
        integrity, version, count_row = _read_database_state(db_path)
    except Exception as exc:
        return [CheckResult("db", "fail", f"Database error: {exc}", str(exc))]

    integrity_ok = bool(integrity and integrity[0] == "ok")
    integrity_check = CheckResult(
        "db_integrity",
        "pass" if integrity_ok else "fail",
        f"SQLite integrity OK: {db_path}"
        if integrity_ok
        else f"SQLite integrity check failed: {integrity}",
    )
    schema_check = _schema_version_check(version)
    roster_count = count_row[0] if count_row else 0
    roster_check = CheckResult(
        "db_roster",
        "pass" if roster_count > 0 else "fail",
        f"Roster: {roster_count} agents active"
        if roster_count > 0
        else "No active agents — run `agency install`",
    )
    return [integrity_check, schema_check, roster_check]


def _provider_validation_map(cfg: AgencyConfig) -> ProviderValidations:
    return {
        id(provider): result
        for provider, result in zip(
            cfg.providers,
            _validate_provider_entries(cfg.providers),
            strict=True,
        )
    }


def _provider_api_key_check(provider: ProviderEntry) -> CheckResult:
    source = "stored in config" if provider.api_key else f"from ${provider.api_key_env}"
    return CheckResult(
        "judge_api_key",
        "pass",
        f"API key present ({_sanitize_diagnostic(source)})",
    )


def _configured_provider_judge_checks(
    provider: ProviderEntry,
    validation: ProviderValidationResult,
) -> list[CheckResult]:
    provider_type = provider.type.strip().lower()
    checks = [] if provider_type in {"ollama", "cli"} else [_provider_api_key_check(provider)]
    if provider_type == "cli":
        message = (
            f"CLI judge {provider.transport} is authenticated and usable"
            if validation.usable
            else f"CLI judge {provider.transport} unavailable: {validation.reason}"
        )
    else:
        endpoint = _safe_endpoint(provider.base_url)
        message = (
            f"Judge provider {provider_type} reachable at {endpoint}"
            if validation.usable
            else (f"Judge provider {provider_type} unreachable at {endpoint}: {validation.reason}")
        )
    checks.append(
        CheckResult(
            "judge_provider",
            "pass" if validation.usable else "fail",
            message,
        )
    )
    return checks


def _legacy_authenticated_judge_checks(
    cfg: AgencyConfig,
    api_key: str,
) -> list[CheckResult]:
    source = "stored in config" if cfg.judge.api_key else f"from ${cfg.judge.api_key_env}"
    api_key_check = CheckResult(
        "judge_api_key",
        "pass",
        f"API key present ({_sanitize_diagnostic(source)})",
    )
    models_url = _join_api_path(cfg.judge.base_url, "/v1/models")
    ok, message = _http_check_authed(models_url, api_key, timeout=5)
    endpoint = _safe_endpoint(cfg.judge.base_url)
    provider_check = CheckResult(
        "judge_provider",
        "pass" if ok else "fail",
        f"Judge endpoint reachable: {endpoint}"
        if ok
        else f"Judge endpoint unreachable: {endpoint}: {message}",
    )
    return [api_key_check, provider_check]


def _ollama_model_check(cfg: AgencyConfig, tags: dict[str, Any]) -> CheckResult:
    entries = tags.get("models", [])
    models = [
        str(item.get("name", ""))[:200]
        for item in (entries[:_MAX_DIAGNOSTIC_MODELS] if isinstance(entries, list) else [])
        if isinstance(item, dict) and item.get("name")
    ]
    model_available = cfg.judge.model in models
    return CheckResult(
        "judge_model",
        "pass" if model_available else "warn",
        f"Judge model '{cfg.judge.model}' available"
        if model_available
        else (f"Judge model '{cfg.judge.model}' not in {len(models)} reported Ollama models"),
    )


def _ollama_judge_checks(cfg: AgencyConfig) -> list[CheckResult]:
    if not cfg.ollama.enabled:
        return [CheckResult("judge_provider", "warn", "Ollama disabled, no provider configured")]

    tags_url = _join_api_path(cfg.ollama.base_url, "/api/tags")
    ok, message = _http_check(tags_url, timeout=5)
    endpoint = _safe_endpoint(cfg.ollama.base_url)
    if not ok:
        return [
            CheckResult(
                "judge_provider",
                "warn",
                f"Legacy Ollama fallback unavailable at {endpoint}: {message}; "
                "deterministic token routing remains available",
            )
        ]

    checks = [CheckResult("judge_provider", "pass", f"Ollama reachable at {endpoint}")]
    tags = _http_get_json(tags_url)
    if tags:
        checks.append(_ollama_model_check(cfg, tags))
    return checks


def _judge_checks(
    cfg: AgencyConfig,
    provider_validations: ProviderValidations,
) -> list[CheckResult]:
    primary_provider = next(
        (provider for provider in cfg.providers if _provider_is_ready(provider)),
        None,
    )
    api_key = cfg.judge.resolve_api_key()
    if primary_provider is not None:
        checks = _configured_provider_judge_checks(
            primary_provider,
            provider_validations[id(primary_provider)],
        )
    elif (not cfg.judge.ollama_mode) and bool(api_key):
        checks = _legacy_authenticated_judge_checks(cfg, api_key)
    elif cfg.judge.ollama_mode or (not api_key and cfg.ollama.enabled):
        checks = _ollama_judge_checks(cfg)
    else:
        checks = [
            CheckResult(
                "judge_provider",
                "warn",
                "No judge provider configured — run `agency configure`",
            )
        ]

    checks.append(
        CheckResult(
            "judge_threshold",
            "pass",
            f"Confidence bypass threshold: {cfg.judge.confidence_bypass_threshold}",
        )
    )
    return checks


def _litellm_check(
    cfg: AgencyConfig,
    *,
    detected: bool,
    health_message: str,
) -> CheckResult:
    enabled = cfg.adapters.litellm.enabled
    if enabled == "false":
        return CheckResult("adapter_litellm", "pass", "litellm: disabled (skipping)")
    if enabled not in {"true", "auto"} or (enabled == "auto" and not detected):
        return CheckResult("adapter_litellm", "pass", "LiteLLM: not detected (skipping)")

    endpoint = _safe_endpoint(cfg.adapters.litellm.base_url)
    if not detected:
        return CheckResult(
            "adapter_litellm",
            "warn" if enabled == "auto" else "fail",
            f"LiteLLM unreachable: {endpoint}: {health_message}",
        )

    adapter_key = cfg.adapters.litellm.resolve_api_key()
    if not adapter_key:
        return CheckResult(
            "adapter_litellm",
            "pass",
            f"LiteLLM reachable (no key configured): {endpoint}",
        )

    auth_ok, auth_message = _http_check_authed(
        _join_api_path(cfg.adapters.litellm.base_url, "/v1/models"),
        adapter_key,
        timeout=3,
    )
    return CheckResult(
        "adapter_litellm",
        "pass" if auth_ok else "warn",
        f"LiteLLM reachable + authenticated: {endpoint}"
        if auth_ok
        else f"LiteLLM reachable but models endpoint failed (auth?): {auth_message}",
    )


def _host_adapter_check(
    name: str,
    enabled: str,
    installation: HostInstallation | None,
) -> CheckResult:
    if enabled == "false":
        return CheckResult(f"adapter_{name}", "pass", f"{name}: disabled (skipping)")

    host = installation or {}
    status = "fail" if enabled == "true" else "warn"
    if host.get("stale_config"):
        return CheckResult(
            f"adapter_{name}",
            status,
            f"{name}: stale config root without a current host executable/state marker",
            str(host.get("native_root") or ""),
        )
    if not host.get("discovered"):
        return CheckResult(
            f"adapter_{name}",
            "fail" if enabled == "true" else "pass",
            f"{name}: enabled in config but not found"
            if enabled == "true"
            else f"{name}: not installed (auto-skip)",
        )
    if not host.get("registered"):
        return CheckResult(
            f"adapter_{name}",
            status,
            f"{name}: host discovered but Agency Runtime is not natively registered",
            f"maturity={host.get('maturity', 'host-discovered')}",
        )
    if host.get("enabled") is False:
        return CheckResult(
            f"adapter_{name}",
            status,
            f"{name}: Agency Runtime is registered but disabled",
        )
    if host.get("loaded") is False:
        return CheckResult(
            f"adapter_{name}",
            "fail",
            f"{name}: Agency Runtime is enabled but native runtime inspection did not load it",
        )
    if host.get("loaded") is True:
        return CheckResult(
            f"adapter_{name}",
            "pass",
            f"{name}: Agency Runtime native plugin loaded and verified",
        )
    if host.get("enabled") is True:
        return CheckResult(
            f"adapter_{name}",
            "warn",
            f"{name}: Agency Runtime enabled; live runtime loading is not provable from cold inventory",
            f"maturity={host.get('maturity', 'enabled-runtime-unverified')}",
        )
    return CheckResult(
        f"adapter_{name}",
        "warn",
        f"{name}: Agency Runtime registered; enablement is not provable from native inventory",
        f"maturity={host.get('maturity', 'registered-enablement-unverified')}",
    )


def _codex_hook_trust_check(
    configured: str,
    host: dict[str, Any] | None,
) -> CheckResult | None:
    """Report the manual Codex command-hook trust boundary without mutating it."""
    if configured == "false" or not host or host.get("registered") is not True:
        return None
    trust_status = str(host.get("hook_trust_status") or "unverified").strip().lower()
    action = str(
        host.get("hook_trust_action")
        or "Run `codex` in a terminal and use its hook-review prompt or `/hooks` TUI."
    )
    if trust_status == "trusted":
        return CheckResult(
            "adapter_codex_hook_trust",
            "pass",
            "codex: Agency Runtime command hooks are trusted",
        )
    if trust_status == "managed":
        return CheckResult(
            "adapter_codex_hook_trust",
            "pass",
            "codex: Agency Runtime command hooks are trusted by managed system policy",
            "Activation proof is reported separately and remains required for runtime readiness.",
        )
    severity = (
        "fail" if configured == "true" and trust_status in {"untrusted", "modified"} else "warn"
    )
    return CheckResult(
        "adapter_codex_hook_trust",
        severity,
        f"codex: command-hook trust is {trust_status}; {action}",
        (
            "Dedicated production containers may grant policy trust through the explicit "
            "system-managed install mode; ordinary plugin installation does not."
        ),
    )


def _adapter_checks(cfg: AgencyConfig) -> list[CheckResult]:
    litellm_ok, litellm_health_message = _http_check(
        _join_api_path(cfg.adapters.litellm.base_url, "/health/liveness"),
        timeout=2,
    )
    checks = [
        _litellm_check(
            cfg,
            detected=litellm_ok,
            health_message=litellm_health_message,
        )
    ]
    host_configuration = (
        ("hermes", cfg.adapters.hermes.enabled),
        ("openclaw", cfg.adapters.openclaw.enabled),
        ("codex", cfg.adapters.codex.enabled),
        ("claude", cfg.adapters.claude.enabled),
        ("zcode", cfg.adapters.zcode.enabled),
    )
    try:
        host_installations = {
            item["host"]: item for item in inspect_host_installations(probe_runtime=False)
        }
    except Exception as exc:
        inventory_status = (
            "fail" if any(enabled == "true" for _name, enabled in host_configuration) else "warn"
        )
        checks.append(
            CheckResult(
                "adapter_host_inventory",
                inventory_status,
                "Native host inventory is unavailable",
                f"inspection failed ({type(exc).__name__})",
            )
        )
        for name, enabled in host_configuration:
            if enabled == "false":
                checks.append(_host_adapter_check(name, enabled, None))
                continue
            checks.append(
                CheckResult(
                    f"adapter_{name}",
                    "fail" if enabled == "true" else "warn",
                    f"{name}: installation state could not be inspected",
                )
            )
        return checks

    for name, enabled in host_configuration:
        host = host_installations.get(name)
        checks.append(_host_adapter_check(name, enabled, host))
        if name == "codex":
            trust_check = _codex_hook_trust_check(enabled, host)
            if trust_check is not None:
                checks.append(trust_check)
    return checks


def _provider_check(
    provider: ProviderEntry,
    validation: ProviderValidationResult,
) -> CheckResult:
    if not validation.usable:
        return CheckResult(
            f"provider_{provider.name}",
            "warn",
            f"{provider.name}: {provider.type} unavailable ({validation.reason})",
        )

    detail = (
        f"transport={provider.transport} installed={validation.installed} "
        f"authenticated={validation.authenticated} usable=True"
        if provider.type.strip().lower() == "cli"
        else f"model={provider.model} auth={provider.auth_method()}"
    )
    return CheckResult(
        f"provider_{provider.name}",
        "pass",
        f"{provider.name}: {provider.type} {detail}",
    )


def _provider_chain_checks(
    cfg: AgencyConfig,
    provider_validations: ProviderValidations,
) -> list[CheckResult]:
    if not cfg.providers:
        return [
            CheckResult(
                "provider_chain",
                "warn",
                "No providers list configured — using legacy judge/ollama fallback. Run `agency configure`.",
            )
        ]

    checks = [
        _provider_check(provider, provider_validations[id(provider)]) for provider in cfg.providers
    ]
    available_count = sum(provider_validations[id(provider)].usable for provider in cfg.providers)
    if available_count == 0:
        checks.append(
            CheckResult(
                "provider_chain",
                "fail",
                "No providers in fallback chain are available — judge will use token-only",
            )
        )
    else:
        chain_names = " → ".join(provider.name for provider in cfg.providers)
        checks.append(
            CheckResult(
                "provider_chain",
                "pass",
                f"Fallback chain ({available_count} available): {chain_names}",
            )
        )
    return checks


def _battery_trial_detail(entry: dict[str, Any]) -> str:
    """Names-only grading tally from one fingerprint entry (AR-360), or "".

    Entries written before trial grading carry no tally and render exactly
    as before; a malformed tally is ignored rather than trusted.
    """

    from agency_runtime.core.harness_battery import grading_label

    mode = entry.get("last_grading_mode")
    trials = entry.get("last_trials")
    if not isinstance(mode, str) or not isinstance(trials, dict):
        return ""
    counts = [trials.get(key) for key in ("requested", "run", "passed")]
    if any(type(count) is not int for count in counts):
        return ""
    requested, run, passed = counts
    return f"{grading_label(mode, requested)}: {passed}/{run} trials"


def _harness_battery_checks() -> list[CheckResult]:
    """Surface the last change-triggered battery outcome per harness (AR-337).

    The check reads only the private fingerprint document: doctor never
    spawns host CLIs. A failed battery is loud, a lost codex attended trust
    is named distinctly, and a harness with no recorded baseline warns until
    its first battery pass. The grading tally (pass^k / pass@k, AR-360) rides
    along as the check detail so the message contract stays unchanged.
    """

    from agency_runtime.core.harness_battery import BATTERY_HOSTS, read_fingerprints

    harnesses = read_fingerprints().get("harnesses", {})
    checks: list[CheckResult] = []
    for host in BATTERY_HOSTS:
        entry = harnesses.get(host)
        name = f"harness_battery_{host}"
        if not isinstance(entry, dict) or not entry.get("last_outcome"):
            checks.append(CheckResult(name, "warn", "no battery baseline recorded"))
            continue
        outcome = str(entry.get("last_outcome"))
        version = str(entry.get("observed_version") or "")
        detail = _battery_trial_detail(entry)
        if outcome == "passed":
            checks.append(CheckResult(name, "pass", version, detail))
        elif outcome == "attended_trust_required":
            checks.append(CheckResult(name, "warn", f"attended trust required ({version})", detail))
        else:
            checks.append(CheckResult(name, "fail", f"battery failed ({version})", detail))
    return checks


def run_doctor(config: AgencyConfig | None = None) -> DoctorReport:
    """Run all health checks and return a structured report."""
    cfg = config or load_config()
    report = DoctorReport()

    report.checks.extend(_config_checks(cfg))
    report.checks.extend(_database_checks(cfg))

    provider_validations = _provider_validation_map(cfg)
    report.checks.extend(_judge_checks(cfg, provider_validations))

    report.checks.extend(_adapter_checks(cfg))

    report.checks.extend(_provider_chain_checks(cfg, provider_validations))
    report.checks.extend(_harness_battery_checks())
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
        lines.append(
            f"  {icon} {_sanitize_diagnostic(check.name)}: {_sanitize_diagnostic(check.message)}"
        )

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
