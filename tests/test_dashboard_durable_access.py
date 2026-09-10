"""AR-436 / ADR-0248: an owner opt-in makes dashboard access durable without a terminal.

Off by default the service token rotates with every process and the page keeps
it in session storage, so a bookmark dies with the tab and every visit needs
``agency dashboard service open``. With ``dashboard.durable_access: true`` the
service reuses one owner-private token across restarts, ``open`` tells the page
to remember it in the browser profile, and ``uninstall`` is the rotation point.
"""

from __future__ import annotations

import json
import os
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import dashboard_service_lifecycle as lifecycle
from agency_runtime.core.config import (
    AgencyConfig,
    DashboardConfig,
    load_config,
    reset_config_cache,
)
from agency_runtime.core.configuration_contracts import (
    RESTART_REQUIRED_PATHS,
    ConfigValidationError,
)
from agency_runtime.core.configuration_schema import validate_config_document
from agency_runtime.core.dashboard_runtime import (
    dashboard_access_token_path,
    load_or_create_durable_dashboard_token,
    open_dashboard_service,
    read_durable_dashboard_token,
    remove_durable_dashboard_token,
    write_dashboard_runtime,
)
from agency_runtime.server import dashboard as dashboard_module


def test_config_opt_in_is_parsed_validated_and_restart_bound(tmp_path: Path) -> None:
    assert DashboardConfig().durable_access is False
    assert validate_config_document({"dashboard": {"port": 7810, "durable_access": True}})[
        "dashboard"
    ] == {"port": 7810, "durable_access": True}
    with pytest.raises(ConfigValidationError):
        validate_config_document({"dashboard": {"durable_access": "sometimes"}})
    with pytest.raises(ConfigValidationError):
        validate_config_document({"dashboard": {"durable": True}})
    assert "dashboard.durable_access" in RESTART_REQUIRED_PATHS

    config_path = tmp_path / "agency.yaml"
    config_path.write_text("dashboard:\n  port: 7811\n  durable_access: true\n", encoding="utf-8")
    os.chmod(config_path, 0o600)
    reset_config_cache()
    try:
        cfg = load_config(config_path, reload=True)
    finally:
        reset_config_cache()
    assert cfg.dashboard == DashboardConfig(port=7811, durable_access=True)


def test_durable_token_is_minted_once_reused_and_removed(tmp_path: Path) -> None:
    assert read_durable_dashboard_token(home_dir=tmp_path) is None
    first = load_or_create_durable_dashboard_token(home_dir=tmp_path)
    assert len(first) >= 32
    path = dashboard_access_token_path(home_dir=tmp_path)
    assert path == tmp_path / ".agency-runtime" / "run" / "dashboard-access.json"
    if os.name != "nt":
        assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert json.loads(path.read_text()) == {"schema_version": 1, "token": first}
    # A second service start reuses the same token.
    assert load_or_create_durable_dashboard_token(home_dir=tmp_path) == first
    assert read_durable_dashboard_token(home_dir=tmp_path) == first
    # An invalid record is refused by the reader and replaced by the loader.
    path.write_text('{"schema_version": 1, "token": "short"}', encoding="utf-8")
    with pytest.raises(ValueError):
        read_durable_dashboard_token(home_dir=tmp_path)
    replaced = load_or_create_durable_dashboard_token(home_dir=tmp_path)
    assert replaced != first and len(replaced) >= 32
    # Removal is the rotation point; a later start mints a new token.
    assert remove_durable_dashboard_token(home_dir=tmp_path) is True
    assert remove_durable_dashboard_token(home_dir=tmp_path) is False
    assert read_durable_dashboard_token(home_dir=tmp_path) is None
    assert load_or_create_durable_dashboard_token(home_dir=tmp_path) not in {first, replaced}


def test_open_marks_the_fragment_durable_only_on_opt_in_and_never_prints_the_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = "durable-token-" + "y" * 40
    write_dashboard_runtime(token=token, port=7810, pid=111, home_dir=tmp_path)
    opened: list[str] = []
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_service_reachable",
        lambda **_kwargs: True,
    )
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.webbrowser.open",
        lambda url, new=0: opened.append(url),
    )
    plain = open_dashboard_service(home_dir=tmp_path)
    durable = open_dashboard_service(home_dir=tmp_path, durable=True)
    assert opened == [
        f"http://127.0.0.1:7810/#token={token}",
        f"http://127.0.0.1:7810/#token={token}&durable=1",
    ]
    assert plain["durable_access"] is False and durable["durable_access"] is True
    assert token not in json.dumps(plain) and token not in json.dumps(durable)


def _run_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, durable: bool) -> str:
    published: list[dict] = []

    class FakeStore:
        def trim_runtime_tables(self, **_kwargs):
            return {}

    class FakeServer:
        server_address = ("127.0.0.1", 8123)

        def __init__(
            self, _store, *, auth_token, broker_token, port, config_path, runtime_control_home
        ):
            self.auth_token = auth_token

        def serve_forever(self, *, poll_interval):
            return None

        def server_close(self):
            return None

    class ImmediateThread:
        def __init__(self, *, target, daemon, name=""):
            self.target = target

        def start(self):
            self.target()

        def join(self, *, timeout):
            return None

    monkeypatch.setattr(
        dashboard_module,
        "load_config",
        lambda *_a, **_k: AgencyConfig(
            dashboard=DashboardConfig(port=8123, durable_access=durable)
        ),
    )
    monkeypatch.setattr(dashboard_module, "Store", lambda *_a, **_k: FakeStore())
    monkeypatch.setattr(dashboard_module, "DashboardHTTPServer", FakeServer)
    monkeypatch.setattr(dashboard_module, "Thread", ImmediateThread)
    monkeypatch.setattr(
        dashboard_module,
        "write_dashboard_runtime",
        lambda **kwargs: (
            published.append(kwargs)
            or {"pid": os.getpid(), "started_at": "2026-09-10T20:00:00+00:00"}
        ),
    )
    monkeypatch.setattr(dashboard_module, "remove_dashboard_runtime", lambda **_k: True)
    monkeypatch.delenv("AGENCY_DB_PATH", raising=False)
    dashboard_module.run_dashboard(service_mode=True, open_browser=False, home_dir=tmp_path)
    return published[0]["token"]


def test_service_mode_reuses_the_durable_token_only_on_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _run_service(tmp_path, monkeypatch, durable=True)
    assert read_durable_dashboard_token(home_dir=tmp_path) == first
    assert _run_service(tmp_path, monkeypatch, durable=True) == first
    # Without the opt-in the token rotates and the durable record is untouched.
    rotating = _run_service(tmp_path, monkeypatch, durable=False)
    assert rotating != first
    assert _run_service(tmp_path, monkeypatch, durable=False) != rotating
    assert read_durable_dashboard_token(home_dir=tmp_path) == first


def test_uninstall_removes_the_durable_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = load_or_create_durable_dashboard_token(home_dir=tmp_path)
    monkeypatch.setattr(lifecycle, "_context", lambda **_k: SimpleNamespace(home_dir=tmp_path))
    monkeypatch.setattr(lifecycle, "_service_lock", lambda _ctx: nullcontext())
    monkeypatch.setattr(
        lifecycle,
        "_uninstall_dashboard_service_locked",
        lambda **_k: {"ok": True, "action": "uninstall"},
    )
    result = lifecycle.uninstall_dashboard_service(home_dir=tmp_path)
    assert result["ok"] is True
    assert result["durable_access_token_removed"] is True
    assert read_durable_dashboard_token(home_dir=tmp_path) is None
    assert token  # the removed token is not reported anywhere
    assert token not in json.dumps(result)


def test_install_flag_persists_the_opt_in_before_installing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from agency_runtime.cli import service_commands
    from agency_runtime.core import installed_config_compatibility as guard

    # The config transaction refuses fields the installed hook projections
    # cannot parse; this test owns no installed projection.
    monkeypatch.setattr(guard, "_installed_projections", lambda: [])
    config_path = tmp_path / "agency.yaml"
    config_path.write_text("dashboard:\n  port: 7810\n", encoding="utf-8")
    os.chmod(config_path, 0o600)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    reset_config_cache()
    calls: list[dict] = []
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_service.install_dashboard_service",
        lambda **kwargs: calls.append(kwargs) or {"ok": True, "action": "install"},
    )
    args = SimpleNamespace(
        dashboard_service_action="install", dry_run=False, durable_access=True, json=False
    )
    try:
        assert service_commands.cmd_dashboard_service(args) == 0
        assert load_config(config_path, reload=True).dashboard.durable_access is True
        # The setting is idempotent: a second install does not rewrite it.
        assert service_commands.cmd_dashboard_service(args) == 0
    finally:
        reset_config_cache()
    assert len(calls) == 2
    assert "durable_access: true" in config_path.read_text()
    out = capsys.readouterr().out
    assert "Durable access is on" in out
