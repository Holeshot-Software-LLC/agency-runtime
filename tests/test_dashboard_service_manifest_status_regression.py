"""Regression coverage for schema-v2 dashboard launcher inspection."""

from __future__ import annotations

from typing import Any

from agency_runtime.cli import service_commands


def test_open_recovery_validates_launcher_before_deciding_manifest_repair(
    monkeypatch,
) -> None:
    import agency_runtime.core.dashboard_runtime as runtime
    import agency_runtime.core.dashboard_service as service

    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        runtime,
        "open_dashboard_service",
        lambda **_kwargs: {"ok": False, "exit_code": 1, "error": "descriptor missing"},
    )
    monkeypatch.setattr(runtime, "dashboard_service_reachable", lambda **_kwargs: True)
    monkeypatch.setattr(
        service,
        "inspect_dashboard_service",
        lambda **kwargs: (
            captured.update(kwargs)
            or {
                "ok": False,
                "exit_code": 1,
                "error": "inspection stopped after validating the launcher",
            }
        ),
    )

    result = service_commands._open_dashboard_with_recovery(open_browser=False)

    assert result["ok"] is False
    assert captured["_validate_launcher"] is True
