"""Tests for the doctor health diagnostics."""

from __future__ import annotations

import os
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
    reset_config_cache()
    yield
    reset_config_cache()


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
        for agent in STARTER_ROSTER:
            store._activate_prevalidated_agent(dict(agent))

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
        for agent in STARTER_ROSTER:
            store._activate_prevalidated_agent(dict(agent))

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
        for agent in STARTER_ROSTER:
            store._activate_prevalidated_agent(dict(agent))

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
        for agent in STARTER_ROSTER:
            store._activate_prevalidated_agent(dict(agent))

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


def test_smoke_all_exercises_generated_host_plugins(monkeypatch, private_installer_launcher):
    """Smoke --all validates every generated host plugin without touching real HOME."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(model="test", ollama_mode=False, base_url="http://127.0.0.1:1"),
        )
        store = Store(cfg.store.resolved_path())
        for agent in STARTER_ROSTER:
            store._activate_prevalidated_agent(dict(agent))
        monkeypatch.setenv("AGENCY_DB_PATH", str(cfg.store.resolved_path()))

        from agency_runtime.core.smoke import run_smoke

        report = run_smoke(all_hosts=True)

        assert report["passed"] is True, [
            check for check in report["checks"] if check["status"] != "pass"
        ]
        check_names = {check["name"] for check in report["checks"]}
        assert {"plugin_hermes", "plugin_openclaw", "plugin_codex", "plugin_claude"} <= check_names


def test_smoke_all_passes_with_empty_active_roster(
    monkeypatch, tmp_path, private_installer_launcher
):
    """Fresh installs can smoke-test before syncing external roster sources."""
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "empty.db"))

    from agency_runtime.core.smoke import run_smoke

    report = run_smoke(all_hosts=True)

    assert report["passed"] is True, [
        check for check in report["checks"] if check["status"] != "pass"
    ]
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
