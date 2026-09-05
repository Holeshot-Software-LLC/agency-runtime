"""Tests for the doctor health diagnostics."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from agency_runtime.core import doctor as doctor_module
from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    ProviderEntry,
    StoreConfig,
    reset_config_cache,
)
from agency_runtime.core.doctor import (
    CheckResult,
    DoctorReport,
    _validate_provider_entries,
    format_report_human,
    run_doctor,
)
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.provider_validation import ProviderValidationResult
from agency_runtime.core.store.sqlite import Store
from tests.runtime_support import is_agency_product_environment_key


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if is_agency_product_environment_key(key) or key == "LITELLM_API_KEY":
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(doctor_module, "inspect_host_installations", lambda **_kwargs: [])
    monkeypatch.setattr(
        doctor_module,
        "_http_check",
        lambda *_args, **_kwargs: (False, "offline test boundary"),
    )
    reset_config_cache()
    yield
    reset_config_cache()


def _activate_one_agent(store: Store) -> None:
    """Satisfy doctor's non-empty count contract without seeding the full roster."""

    store._activate_prevalidated_agent(dict(STARTER_ROSTER[0]))


def test_doctor_returns_report():
    """Doctor returns a DoctorReport with checks."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(
                model="test",
                ollama_mode=False,
                base_url="http://127.0.0.1:1",
            ),
        )
        store = Store(cfg.store.resolved_path())
        _activate_one_agent(store)

        report = run_doctor(cfg)

        assert isinstance(report, DoctorReport)
        assert len(report.checks) > 0
        check_names = [check.name for check in report.checks]
        assert "db_integrity" in check_names
        assert "db_roster" in check_names


def test_doctor_escapes_terminal_controls_in_names_and_messages() -> None:
    report = DoctorReport(
        [
            CheckResult("provider_\x1b[31m", "warn", "model=\x9bhostile"),
        ]
    )

    rendered = format_report_human(report)
    payload = report.to_dict()

    assert "\x1b" not in rendered
    assert "\x9b" not in rendered
    assert "\\u001b" in rendered
    assert "\x1b" not in payload["checks"][0]["name"]


def test_doctor_keeps_safe_endpoint_when_sentence_punctuation_follows_port() -> None:
    report = DoctorReport(
        [
            CheckResult(
                "judge_provider",
                "fail",
                "Ollama unreachable at http://127.0.0.1:11434: network error",
            )
        ]
    )

    message = report.to_dict()["checks"][0]["message"]

    assert message == "Ollama unreachable at http://127.0.0.1:11434: network error"
    assert "<invalid endpoint>" not in message


@pytest.mark.parametrize(
    ("provider_type", "header"),
    [("openai-compatible", "Authorization"), ("anthropic", "X-api-key")],
)
def test_doctor_legacy_authenticated_probe_uses_redirect_refusing_opener(
    provider_type: str,
    header: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def open_request(request, **kwargs):
        captured["request"] = request
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(doctor_module, "open_no_redirect", open_request)

    ok, message = doctor_module._http_check_authed(
        "https://provider.invalid/v1/models",
        "secret",
        timeout=1,
        provider_type=provider_type,
    )

    assert ok is True
    assert message == "HTTP 200"
    assert captured["timeout"] == 1
    assert captured["request"].headers[header] in {
        "Bearer secret",
        "secret",
    }


def test_doctor_detects_empty_roster():
    """Doctor fails when roster is empty."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(model="test", ollama_mode=False, base_url="http://127.0.0.1:1"),
        )
        Store(cfg.store.resolved_path())

        report = run_doctor(cfg)
        roster_check = next(c for c in report.checks if c.name == "db_roster")
        assert roster_check.status == "fail"


def test_doctor_fails_when_the_store_is_newer_than_this_runtime():
    """A store ahead of the runtime disables everything, so doctor must say so.

    On 2026-08-14 this check reported ``Schema version: 46`` with a green tick
    while the running launcher was 45 and refused that exact store. Every hook
    on the machine failed open for over an hour, staffing nothing, and the one
    diagnostic meant to catch it agreed that all was well.
    """

    from agency_runtime.core.store.schema import SCHEMA_VERSION

    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(model="test", ollama_mode=False, base_url="http://127.0.0.1:1"),
        )
        store = Store(cfg.store.resolved_path())
        for agent in STARTER_ROSTER:
            store._activate_prevalidated_agent(agent)
        conn = sqlite3.connect(cfg.store.resolved_path())
        try:
            conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION + 1,))
            conn.commit()
        finally:
            conn.close()

        report = run_doctor(cfg)

    schema_check = next(c for c in report.checks if c.name == "db_schema")
    assert schema_check.status == "fail"
    assert str(SCHEMA_VERSION + 1) in schema_check.message
    assert "Reinstall" in schema_check.message
    assert report.exit_code == 1


def test_doctor_warns_when_the_store_still_trails_this_runtime():
    """The window before the first open is exactly when drift is preventable."""

    from agency_runtime.core.store.schema import SCHEMA_VERSION

    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(model="test", ollama_mode=False, base_url="http://127.0.0.1:1"),
        )
        store = Store(cfg.store.resolved_path())
        for agent in STARTER_ROSTER:
            store._activate_prevalidated_agent(agent)
        conn = sqlite3.connect(cfg.store.resolved_path())
        try:
            conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION - 1,))
            conn.commit()
        finally:
            conn.close()

        report = run_doctor(cfg)

    schema_check = next(c for c in report.checks if c.name == "db_schema")
    assert schema_check.status == "warn"
    assert str(SCHEMA_VERSION - 1) in schema_check.message


def test_doctor_exit_codes():
    """Exit code is 0 (healthy), 1 (failed), or 2 (degraded)."""
    from agency_runtime.core.doctor import CheckResult

    report = DoctorReport()
    assert report.exit_code == 0

    report2 = DoctorReport()
    report2.checks = [
        CheckResult("ok", "pass", "fine"),
        CheckResult("maybe", "warn", "watch"),
    ]
    assert report2.exit_code == 2

    report3 = DoctorReport()
    report3.checks = [
        CheckResult("bad", "fail", "broken"),
    ]
    assert report3.exit_code == 1


def test_doctor_json_serializable():
    """Report is JSON-serializable."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(model="test", ollama_mode=False, base_url="http://127.0.0.1:1"),
        )
        store = Store(cfg.store.resolved_path())
        _activate_one_agent(store)

        report = run_doctor(cfg)
        data = report.to_dict()
        assert "status" in data
        assert "exit_code" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)


def test_doctor_distinguishes_host_discovery_from_native_registration(monkeypatch):
    """A discovered host is not reported as a working Agency integration."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(model="test", ollama_mode=False, base_url="http://127.0.0.1:1"),
        )
        store = Store(cfg.store.resolved_path())
        _activate_one_agent(store)

        monkeypatch.setattr(
            "agency_runtime.core.doctor.inspect_host_installations",
            lambda **_kwargs: [
                {
                    "host": "openclaw",
                    "discovered": True,
                    "registered": False,
                    "enabled": None,
                    "loaded": None,
                    "stale_config": False,
                    "maturity": "host-discovered",
                }
            ],
        )
        report = run_doctor(cfg)
        openclaw_check = next(c for c in report.checks if c.name == "adapter_openclaw")
        assert openclaw_check.status == "warn"
        assert "not natively registered" in openclaw_check.message


def test_doctor_accepts_yolo_profile():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(model="test", ollama_mode=False, base_url="http://127.0.0.1:1"),
            profile="yolo",
        )
        store = Store(cfg.store.resolved_path())
        _activate_one_agent(store)

        report = run_doctor(cfg)
        profile_check = next(c for c in report.checks if c.name == "config_profile")
    assert profile_check.status == "pass"


def test_provider_validation_is_parallel_and_preserves_order(monkeypatch):
    providers = tuple(
        ProviderEntry(
            name=f"provider-{index}",
            type="ollama",
            model="model",
            base_url="http://127.0.0.1:11434",
        )
        for index in range(8)
    )

    def validate(provider, **_kwargs):
        time.sleep(0.04)
        return ProviderValidationResult(
            provider.name,
            provider.type,
            True,
            True,
        )

    monkeypatch.setattr("agency_runtime.core.doctor.validate_provider", validate)
    started = time.monotonic()
    results = _validate_provider_entries(providers)

    assert time.monotonic() - started < 0.2
    assert [result.name for result in results] == [f"provider-{index}" for index in range(8)]


def test_smoke_all_exercises_generated_host_plugins_with_fresh_roster(
    private_installer_launcher,
):
    """Smoke --all validates every plugin from its own isolated fresh Store."""
    from agency_runtime.core.smoke import run_smoke

    report = run_smoke(all_hosts=True)

    assert report["passed"] is True, [
        check for check in report["checks"] if check["status"] != "pass"
    ]
    check_names = {check["name"] for check in report["checks"]}
    assert {"plugin_hermes", "plugin_openclaw", "plugin_codex", "plugin_claude"} <= check_names
    roster_check = next(
        check for check in report["checks"] if check["name"] == "routing_roster_available"
    )
    assert roster_check["detail"]["source"] == "starter_roster"


def test_openclaw_smoke_uses_static_validation_when_node_is_unavailable(
    monkeypatch, tmp_path, private_installer_launcher
):
    from agency_runtime.core import smoke
    from agency_runtime.core.installer import install_agent_adapter

    (tmp_path / ".openclaw").mkdir()
    installed = install_agent_adapter("openclaw", home_dir=tmp_path)
    assert installed["ok"] is True

    monkeypatch.delenv("AGENCY_CI_NODE", raising=False)
    monkeypatch.setattr(smoke.shutil, "which", lambda _name: None)
    detail = smoke._smoke_openclaw_plugin("openclaw", Path(installed["plugin_path"]))

    assert detail["format"] == "openclaw-js"
    assert detail["syntax_check"] == "skipped: node unavailable"


def _start_attempt(store, trace_id: str, host: str) -> str:
    import hashlib

    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id=trace_id,
        request_fingerprint=hashlib.sha256(trace_id.encode("utf-8")).hexdigest(),
        request_kind="nontrivial",
        host=host,
    )
    return str(started["attempt_token"])


def test_database_checks_report_attempts_stuck_past_their_lease(tmp_path: Path) -> None:
    """AR-398 criterion 4: a run left in_progress past its lease is named, per host."""

    from agency_runtime.core import doctor
    from agency_runtime.core.store.sqlite import Store

    path = tmp_path / "agency.db"
    store = Store(path)
    _start_attempt(store, "stuck-one", "openclaw")
    _start_attempt(store, "stuck-two", "openclaw")
    _start_attempt(store, "still-running", "hermes")
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE runs SET preflight_lease_expires_at = '2000-01-01T00:00:00.000000+00:00' "
            "WHERE trace_id IN ('stuck-one', 'stuck-two')"
        )
        connection.commit()
    finally:
        connection.close()

    cfg = AgencyConfig(store=StoreConfig(db_path=str(path)))
    checks = doctor._database_checks(cfg)

    stuck = next(c for c in checks if c.name == "db_preflight_stuck")
    assert stuck.status == "warn"
    assert stuck.message.startswith(
        "2 preflight attempt(s) left in_progress past their lease (openclaw 2)"
    )
    assert "no receipt" in stuck.message
    assert stuck.detail.startswith("oldest started 20")


def test_database_checks_pass_when_no_attempt_is_stuck(tmp_path: Path) -> None:
    from agency_runtime.core import doctor
    from agency_runtime.core.store.sqlite import Store

    path = tmp_path / "agency.db"
    store = Store(path)
    token = _start_attempt(store, "closed", "claude")
    assert store.fail_preflight_attempt(
        session_id="session", trace_id="closed", attempt_token=token
    )
    _start_attempt(store, "live", "claude")  # inside its lease

    cfg = AgencyConfig(store=StoreConfig(db_path=str(path)))
    checks = doctor._database_checks(cfg)

    stuck = next(c for c in checks if c.name == "db_preflight_stuck")
    assert stuck.status == "pass"
    assert [c.name for c in checks] == [
        "db_integrity",
        "db_schema",
        "db_roster",
        "db_preflight_stuck",
    ]
