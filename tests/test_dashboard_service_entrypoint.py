"""Focused contract tests for the minimal persistent dashboard entry point."""

from __future__ import annotations

import sys
from types import ModuleType

from agency_runtime.server import dashboard_service


def test_dashboard_service_entrypoint_rejects_any_noncanonical_argument_shape(
    capsys,
) -> None:
    for arguments in (
        (),
        ("--config",),
        ("--config", ""),
        ("--port", "7810"),
        ("--config", "agency.yaml", "--extra"),
    ):
        assert dashboard_service.main(arguments) == 2

    assert "usage:" in capsys.readouterr().err


def test_dashboard_service_entrypoint_imports_only_after_validation(
    monkeypatch,
) -> None:
    observed: list[dict[str, object]] = []
    module = ModuleType("agency_runtime.server.dashboard")
    module.run_dashboard = lambda **kwargs: observed.append(kwargs)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "agency_runtime.server.dashboard", module)

    assert dashboard_service.main(("--config", "C:/Agency/agency.yaml")) == 0
    assert observed == [
        {
            "open_browser": False,
            "service_mode": True,
            "config_path": "C:/Agency/agency.yaml",
        }
    ]
