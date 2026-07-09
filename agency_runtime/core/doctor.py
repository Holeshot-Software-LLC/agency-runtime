"""Health diagnostics for `agency doctor`.

Checks every subsystem and returns a structured report.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sqlite3
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agency_runtime.core.config import AgencyConfig, load_config


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
                {"name": c.name, "status": c.status, "message": c.message, "detail": c.detail}
                for c in self.checks
            ],
        }


def _http_check(url: str, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200, f"HTTP {resp.status}"
    except Exception as exc:
        return False, str(exc)[:100]


def _http_check_authed(url: str, api_key: str, timeout: float = 2.0) -> tuple[bool, str]:
    """HTTP check with Authorization header for authenticated endpoints."""
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200, f"HTTP {resp.status}"
    except Exception as exc:
        return False, str(exc)[:100]


def _http_get_json(url: str, timeout: float = 2.0) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def run_doctor(config: AgencyConfig | None = None) -> DoctorReport:
    """Run all health checks and return a structured report."""
    cfg = config or load_config()
    report = DoctorReport()

    # ── Config checks ─────────────────────────────────────────
    config_path_str = cfg.config_path or "(defaults only)"
    if cfg.config_path and Path(cfg.config_path).exists():
        report.checks.append(CheckResult("config_file", "pass", f"Config file: {cfg.config_path}"))
    else:
        report.checks.append(CheckResult("config_file", "warn", "No config file found — using bundled defaults"))

    valid_profiles = {"local-only", "standard", "power"}
    if cfg.profile in valid_profiles:
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
    api_key = cfg.judge.resolve_api_key()

    # Determine provider path:
    #   - ollama_mode=True → always Ollama path
    #   - ollama_mode=False + api_key present (direct or env) → API-key provider path
    #   - ollama_mode=False + no api_key → Ollama fallback path
    is_api_key_provider = (not cfg.judge.ollama_mode) and bool(api_key)

    if is_api_key_provider:
        # API-key based provider (LiteLLM, OpenAI, Anthropic, custom endpoint)
        if cfg.judge.api_key:
            source = "stored in config"
        elif cfg.judge.api_key_env:
            source = f"from ${cfg.judge.api_key_env}"
        else:
            source = "(unknown)"

        report.checks.append(CheckResult("judge_api_key", "pass",
            f"API key present ({source})"))

        ok, msg = _http_check_authed(f"{cfg.judge.base_url}/models", api_key, timeout=5)
        if ok:
            report.checks.append(CheckResult("judge_provider", "pass",
                f"Judge endpoint reachable: {cfg.judge.base_url}"))
        else:
            # Try /v1/models as fallback (some providers use /v1 prefix)
            ok2, msg2 = _http_check_authed(f"{cfg.judge.base_url}/v1/models", api_key, timeout=5)
            if ok2:
                report.checks.append(CheckResult("judge_provider", "pass",
                    f"Judge endpoint reachable: {cfg.judge.base_url}/v1"))
            else:
                report.checks.append(CheckResult("judge_provider", "fail",
                    f"Judge endpoint unreachable: {cfg.judge.base_url}: {msg}"))
    elif cfg.judge.ollama_mode or (not api_key and cfg.ollama.enabled):
        if cfg.ollama.enabled:
            ok, msg = _http_check(f"{cfg.ollama.base_url}/api/tags", timeout=5)
            if ok:
                report.checks.append(CheckResult("judge_provider", "pass",
                    f"Ollama reachable at {cfg.ollama.base_url}"))
                tags = _http_get_json(f"{cfg.ollama.base_url}/api/tags")
                if tags:
                    models = [m.get("name", "") for m in tags.get("models", [])]
                    if cfg.judge.model in models:
                        report.checks.append(CheckResult("judge_model", "pass",
                            f"Judge model '{cfg.judge.model}' available"))
                    else:
                        report.checks.append(CheckResult("judge_model", "warn",
                            f"Judge model '{cfg.judge.model}' not in Ollama models: {models[:5]}",
                            f"Available: {', '.join(models[:10])}"))
            else:
                report.checks.append(CheckResult("judge_provider", "fail",
                    f"Ollama unreachable at {cfg.ollama.base_url}: {msg}"))
        else:
            report.checks.append(CheckResult("judge_provider", "warn", "Ollama disabled, no provider configured"))
    else:
        report.checks.append(CheckResult("judge_provider", "warn",
            "No judge provider configured — run `agency configure`"))

    report.checks.append(CheckResult("judge_threshold", "pass",
        f"Confidence bypass threshold: {cfg.judge.confidence_bypass_threshold}"))

    # ── Adapter checks ────────────────────────────────────────
    def check_adapter(name: str, enabled: str, detected: bool):
        if enabled == "false":
            report.checks.append(CheckResult(f"adapter_{name}", "pass",
                f"{name}: disabled (skipping)"))
            return

        if name == "litellm":
            if enabled == "true" or (enabled == "auto" and detected):
                # Health check (unauthenticated)
                ok, msg = _http_check(f"{cfg.adapters.litellm.base_url}/health/liveness", timeout=3)
                if ok:
                    # Verify auth works with configured key
                    adapter_key = cfg.adapters.litellm.resolve_api_key()
                    if adapter_key:
                        auth_ok, auth_msg = _http_check_authed(
                            f"{cfg.adapters.litellm.base_url}/v1/models",
                            adapter_key,
                            timeout=3,
                        )
                        if auth_ok:
                            report.checks.append(CheckResult("adapter_litellm", "pass",
                                f"LiteLLM reachable + authenticated: {cfg.adapters.litellm.base_url}"))
                        else:
                            report.checks.append(CheckResult("adapter_litellm", "warn",
                                f"LiteLLM reachable but models endpoint failed (auth?): {auth_msg}"))
                    else:
                        report.checks.append(CheckResult("adapter_litellm", "pass",
                            f"LiteLLM reachable (no key configured): {cfg.adapters.litellm.base_url}"))
                else:
                    status = "warn" if enabled == "auto" else "fail"
                    report.checks.append(CheckResult("adapter_litellm", status,
                        f"LiteLLM unreachable: {cfg.adapters.litellm.base_url}: {msg}"))
            else:
                report.checks.append(CheckResult("adapter_litellm", "pass",
                    "LiteLLM: not detected (skipping)"))
            return

        exe = shutil.which(name)
        mod = importlib.util.find_spec(name) is not None
        installed = bool(exe or mod)
        if installed:
            report.checks.append(CheckResult(f"adapter_{name}", "pass",
                f"{name}: installed ({exe or 'module'})"))
        elif enabled == "true":
            report.checks.append(CheckResult(f"adapter_{name}", "fail",
                f"{name}: enabled in config but not found"))
        else:
            report.checks.append(CheckResult(f"adapter_{name}", "pass",
                f"{name}: not installed (auto-skip)"))

    # Detect adapters
    litellm_ok, _ = _http_check(f"{cfg.adapters.litellm.base_url}/health/liveness", timeout=2)
    check_adapter("litellm", cfg.adapters.litellm.enabled, litellm_ok)
    check_adapter("hermes", cfg.adapters.hermes.enabled, False)
    check_adapter("openclaw", cfg.adapters.openclaw.enabled, False)
    check_adapter("codex", cfg.adapters.codex.enabled, False)
    check_adapter("claude", cfg.adapters.claude.enabled, False)

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
        lines.append(f"  {icon} {check.name}: {check.message}")

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
