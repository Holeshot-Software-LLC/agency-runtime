"""Tests for the doctor health diagnostics."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    StoreConfig,
    reset_config_cache,
)
from agency_runtime.core.doctor import DoctorReport, run_doctor
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.store.sqlite import Store


@pytest.fixture(autouse=True)
def _clean_env():
    for key in list(os.environ):
        if key.startswith("AGENCY_") or key == "LITELLM_API_KEY":
            os.environ.pop(key, None)
    reset_config_cache()
    yield
    reset_config_cache()


def test_doctor_returns_report():
    """Doctor returns a DoctorReport with checks."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(model="test", ollama_mode=False, base_url="http://127.0.0.1:1"),
        )
        store = Store(cfg.store.resolved_path())
        for agent in STARTER_ROSTER:
            store.activate_agent(dict(agent))

        report = run_doctor(cfg)
        assert isinstance(report, DoctorReport)
        assert len(report.checks) > 0
        check_names = [c.name for c in report.checks]
        assert "db_integrity" in check_names
        assert "db_roster" in check_names


def test_doctor_detects_empty_roster():
    """Doctor fails when roster is empty."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(model="test", ollama_mode=False, base_url="http://127.0.0.1:1"),
        )
        Store(cfg.store.resolved_path())

        report = run_doctor(cfg)
        roster_check = [c for c in report.checks if c.name == "db_roster"][0]
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
            store.activate_agent(dict(agent))

        report = run_doctor(cfg)
        data = report.to_dict()
        assert "status" in data
        assert "exit_code" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)


def test_doctor_uses_host_detection_for_path_only_hosts(monkeypatch):
    """Doctor treats OpenClaw's config directory as install evidence."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(model="test", ollama_mode=False, base_url="http://127.0.0.1:1"),
        )
        store = Store(cfg.store.resolved_path())
        for agent in STARTER_ROSTER:
            store.activate_agent(dict(agent))

        monkeypatch.setattr("agency_runtime.core.doctor.detect_installed_agents", lambda: ["openclaw"])
        report = run_doctor(cfg)
        openclaw_check = [c for c in report.checks if c.name == "adapter_openclaw"][0]
        assert openclaw_check.status == "pass"
        assert "installed" in openclaw_check.message
        assert "not installed" not in openclaw_check.message


def test_smoke_all_exercises_generated_host_plugins(monkeypatch):
    """Smoke --all validates every generated host plugin without touching real HOME."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = AgencyConfig(
            store=StoreConfig(db_path=f"{tmp}/test.db"),
            judge=JudgeConfig(model="test", ollama_mode=False, base_url="http://127.0.0.1:1"),
        )
        store = Store(cfg.store.resolved_path())
        for agent in STARTER_ROSTER:
            store.activate_agent(dict(agent))
        monkeypatch.setenv("AGENCY_DB_PATH", str(cfg.store.resolved_path()))

        from agency_runtime.core.smoke import run_smoke
        report = run_smoke(all_hosts=True)

        assert report["passed"] is True
        check_names = {check["name"] for check in report["checks"]}
        assert {"plugin_hermes", "plugin_openclaw", "plugin_codex", "plugin_claude"} <= check_names


def test_smoke_all_passes_with_empty_active_roster(monkeypatch, tmp_path):
    """Fresh installs can smoke-test before syncing external roster sources."""
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "empty.db"))

    from agency_runtime.core.smoke import run_smoke
    report = run_smoke(all_hosts=True)

    assert report["passed"] is True
    roster_check = [check for check in report["checks"] if check["name"] == "routing_roster_available"][0]
    assert roster_check["detail"]["source"] == "starter_roster"
