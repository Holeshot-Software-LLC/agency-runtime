"""Complete doctor diagnostic branches without contacting external services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import doctor
from agency_runtime.core.config import (
    AdapterEntryConfig,
    AdaptersConfig,
    AgencyConfig,
    JudgeConfig,
    OllamaConfig,
    ProviderEntry,
    StoreConfig,
)
from agency_runtime.core.doctor import CheckResult, DoctorReport
from agency_runtime.core.provider_validation import ProviderValidationResult


def _validation(provider: ProviderEntry, *, usable: bool, reason: str = "offline") -> Any:
    return ProviderValidationResult(
        provider.name,
        provider.type,
        usable,
        usable,
        reason,
        installed=usable,
        authenticated=usable,
    )


def test_doctor_sanitization_handles_invalid_ipv6_secrets_and_v1_paths() -> None:
    assert doctor._safe_endpoint("relative") == "<invalid endpoint>"
    assert doctor._safe_endpoint("http://[::1]:7800/path?secret=x") == "http://[::1]:7800"
    assert (
        doctor._sanitize_diagnostic(
            "secret https://user:pass@example.invalid/path?q=secret",
            secrets=("", "secret"),
        )
        == "<redacted> https://example.invalid"
    )
    assert doctor._join_api_path("https://example.invalid/v1", "/v1/models") == (
        "https://example.invalid/v1/models"
    )


def test_doctor_report_healthy_status_and_human_format() -> None:
    report = DoctorReport([CheckResult("ok", "pass", "ready")])
    assert report.overall_status == "HEALTHY"
    assert "HEALTHY — all checks passed" in doctor.format_report_human(report)


def test_codex_hook_trust_diagnostic_preserves_the_manual_security_boundary() -> None:
    assert doctor._codex_hook_trust_check("false", {"registered": True}) is None
    assert doctor._codex_hook_trust_check("true", None) is None

    trusted = doctor._codex_hook_trust_check(
        "true",
        {"registered": True, "hook_trust_status": "trusted"},
    )
    assert trusted is not None and trusted.status == "pass"

    untrusted = doctor._codex_hook_trust_check(
        "true",
        {
            "registered": True,
            "hook_trust_status": "untrusted",
            "hook_trust_action": "Open `/hooks` now.",
        },
    )
    assert untrusted is not None and untrusted.status == "fail"
    assert "Open `/hooks` now" in untrusted.message

    modified = doctor._codex_hook_trust_check(
        "auto",
        {"registered": True, "hook_trust_status": "modified"},
    )
    assert modified is not None and modified.status == "warn"

    unverified = doctor._codex_hook_trust_check("true", {"registered": True})
    assert unverified is not None and unverified.status == "warn"
    assert "never grant hook trust automatically" in unverified.detail


def test_http_json_probe_rejects_oversized_and_non_object_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Response:
        status = 200

        def __init__(self, payload: bytes) -> None:
            self.payload = payload

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int) -> bytes:
            return self.payload

    monkeypatch.setattr(
        doctor,
        "open_no_redirect",
        lambda *_args, **_kwargs: _Response(b"x" * (doctor._MAX_HTTP_JSON_BYTES + 1)),
    )
    assert doctor._http_get_json("https://example.invalid") is None
    monkeypatch.setattr(
        doctor,
        "open_no_redirect",
        lambda *_args, **_kwargs: _Response(b"[]"),
    )
    assert doctor._http_get_json("https://example.invalid") is None


def test_network_and_provider_probe_exceptions_are_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        doctor,
        "open_no_redirect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("secret")),
    )
    assert doctor._http_check_authed("https://example.invalid", "key") == (
        False,
        "network error (TimeoutError)",
    )
    assert doctor._http_get_json("https://example.invalid") is None

    provider = ProviderEntry(
        name="remote",
        model="model",
        base_url="https://example.invalid/v1",
        api_key="key",
    )
    monkeypatch.setattr(
        doctor,
        "validate_provider",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("private")),
    )
    result = doctor._validate_provider_entries((provider,))[0]
    assert result.reason == "provider validation failed unexpectedly"


def test_config_check_reports_an_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    checks = doctor._config_checks(AgencyConfig(config_path=str(path)))
    assert checks[0].status == "pass"
    assert str(path) in checks[0].message


def test_database_checks_report_missing_database_without_mutating(tmp_path: Path) -> None:
    cfg = AgencyConfig(store=StoreConfig(db_path=str(tmp_path / "missing.db")))
    with pytest.raises(FileNotFoundError, match="does not exist"):
        doctor._read_database_state(cfg.store.resolved_path())
    checks = doctor._database_checks(cfg)
    assert checks == [
        CheckResult(
            "db",
            "fail",
            f"Database error: database does not exist: {cfg.store.resolved_path()}",
            f"database does not exist: {cfg.store.resolved_path()}",
        )
    ]


def test_configured_cli_provider_reports_transport_state() -> None:
    provider = ProviderEntry(
        name="codex",
        type="cli",
        transport="codex",
        model="gpt-5",
    )
    passed = doctor._configured_provider_judge_checks(
        provider,
        _validation(provider, usable=True),
    )
    failed = doctor._configured_provider_judge_checks(
        provider,
        _validation(provider, usable=False, reason="not authenticated"),
    )
    assert passed[0].status == "pass"
    assert "authenticated and usable" in passed[0].message
    assert failed[0].status == "fail"
    assert "not authenticated" in failed[0].message


@pytest.mark.parametrize("stored", [False, True])
def test_legacy_authenticated_judge_checks_both_key_sources(
    monkeypatch: pytest.MonkeyPatch,
    stored: bool,
) -> None:
    monkeypatch.setattr(doctor, "_http_check_authed", lambda *_args, **_kwargs: (True, "ok"))
    cfg = AgencyConfig(
        judge=JudgeConfig(
            model="model",
            base_url="https://example.invalid/v1",
            api_key="key" if stored else "",
            api_key_env="JUDGE_KEY",
        )
    )
    checks = doctor._legacy_authenticated_judge_checks(cfg, "resolved")
    assert checks[0].status == "pass"
    assert ("stored in config" if stored else "from $JUDGE_KEY") in checks[0].message
    assert checks[1].status == "pass"


def test_ollama_model_and_provider_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    disabled = AgencyConfig(ollama=OllamaConfig(enabled=False))
    assert doctor._ollama_judge_checks(disabled)[0].status == "warn"

    cfg = AgencyConfig(
        judge=JudgeConfig(model="wanted", ollama_mode=True),
        ollama=OllamaConfig(enabled=True, model="wanted"),
    )
    assert doctor._ollama_model_check(cfg, {"models": "invalid"}).status == "warn"
    assert (
        doctor._ollama_model_check(
            cfg,
            {"models": [{"name": "wanted"}, "invalid", {}]},
        ).status
        == "pass"
    )
    monkeypatch.setattr(doctor, "_http_check", lambda *_args, **_kwargs: (True, "HTTP 200"))
    monkeypatch.setattr(doctor, "_http_get_json", lambda *_args, **_kwargs: {"models": []})
    checks = doctor._ollama_judge_checks(cfg)
    assert [check.name for check in checks] == ["judge_provider", "judge_model"]
    monkeypatch.setattr(doctor, "_http_get_json", lambda *_args, **_kwargs: None)
    assert len(doctor._ollama_judge_checks(cfg)) == 1

    monkeypatch.setattr(doctor, "_http_check", lambda *_args, **_kwargs: (False, "offline"))
    unavailable = doctor._ollama_judge_checks(cfg)
    assert unavailable[0].status == "warn"
    assert "deterministic token routing remains available" in unavailable[0].message
    report = DoctorReport(unavailable)
    assert report.overall_status == "DEGRADED"
    assert report.exit_code == 2


def test_judge_checks_legacy_and_unconfigured_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        doctor,
        "_legacy_authenticated_judge_checks",
        lambda *_args, **_kwargs: [CheckResult("judge_provider", "pass", "legacy")],
    )
    legacy = AgencyConfig(
        judge=JudgeConfig(
            model="model",
            base_url="https://example.invalid/v1",
            api_key="key",
            ollama_mode=False,
        ),
        ollama=OllamaConfig(enabled=False),
    )
    assert doctor._judge_checks(legacy, {})[0].message == "legacy"

    empty = AgencyConfig(
        judge=JudgeConfig(model="", ollama_mode=False),
        ollama=OllamaConfig(enabled=False),
    )
    checks = doctor._judge_checks(empty, {})
    assert "No judge provider configured" in checks[0].message


def _with_litellm(entry: AdapterEntryConfig) -> AgencyConfig:
    return AgencyConfig(adapters=AdaptersConfig(litellm=entry))


def test_litellm_check_disabled_undetected_unreachable_and_keyless() -> None:
    disabled = doctor._litellm_check(
        _with_litellm(AdapterEntryConfig(enabled="false")),
        detected=False,
        health_message="offline",
    )
    assert disabled.status == "pass"

    skipped = doctor._litellm_check(
        _with_litellm(AdapterEntryConfig(enabled="invalid")),
        detected=False,
        health_message="offline",
    )
    assert "not detected" in skipped.message

    unreachable = doctor._litellm_check(
        _with_litellm(AdapterEntryConfig(enabled="true", base_url="http://127.0.0.1:4000")),
        detected=False,
        health_message="connection refused",
    )
    assert unreachable.status == "fail"

    keyless = doctor._litellm_check(
        _with_litellm(AdapterEntryConfig(enabled="true", base_url="http://127.0.0.1:4000")),
        detected=True,
        health_message="ok",
    )
    assert "no key configured" in keyless.message


def test_litellm_check_probes_models_when_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def probe(url: str, key: str, **_kwargs: Any) -> tuple[bool, str]:
        calls.append((url, key))
        return True, "HTTP 200"

    monkeypatch.setattr(doctor, "_http_check_authed", probe)
    result = doctor._litellm_check(
        _with_litellm(
            AdapterEntryConfig(
                enabled="true",
                base_url="http://127.0.0.1:4000",
                api_key="secret",
            )
        ),
        detected=True,
        health_message="ok",
    )
    assert result.status == "pass"
    assert calls == [("http://127.0.0.1:4000/v1/models", "secret")]


@pytest.mark.parametrize(
    ("enabled", "host", "status", "message"),
    [
        ("false", None, "pass", "disabled"),
        ("auto", {"stale_config": True, "native_root": "old"}, "warn", "stale"),
        ("true", {"discovered": False}, "fail", "not found"),
        ("auto", {"discovered": False}, "pass", "auto-skip"),
        (
            "auto",
            {"discovered": True, "registered": True, "enabled": False},
            "warn",
            "disabled",
        ),
        (
            "auto",
            {"discovered": True, "registered": True, "enabled": True, "loaded": False},
            "fail",
            "did not load",
        ),
        (
            "auto",
            {"discovered": True, "registered": True, "enabled": True, "loaded": True},
            "pass",
            "loaded and verified",
        ),
        (
            "auto",
            {"discovered": True, "registered": True, "enabled": True},
            "warn",
            "loading is not provable",
        ),
        (
            "auto",
            {"discovered": True, "registered": True, "enabled": None},
            "warn",
            "enablement is not provable",
        ),
    ],
)
def test_host_adapter_check_maturity_matrix(
    enabled: str,
    host: dict[str, Any] | None,
    status: str,
    message: str,
) -> None:
    result = doctor._host_adapter_check("codex", enabled, host)
    assert result.status == status
    assert message in result.message


def test_provider_and_chain_unavailable_branches() -> None:
    provider = ProviderEntry(
        name="remote",
        model="model",
        base_url="https://example.invalid/v1",
        api_key="key",
    )
    validation = _validation(provider, usable=False, reason="offline")
    assert doctor._provider_check(provider, validation).status == "warn"
    checks = doctor._provider_chain_checks(
        AgencyConfig(providers=(provider,)),
        {id(provider): validation},
    )
    assert checks[-1].status == "fail"
    assert "token-only" in checks[-1].message


def test_human_report_degraded_and_failed_outcomes() -> None:
    degraded = doctor.format_report_human(DoctorReport([CheckResult("warn", "warn", "later")]))
    failed = doctor.format_report_human(DoctorReport([CheckResult("fail", "fail", "broken")]))
    assert "DEGRADED" in degraded
    assert "FAILED" in failed
