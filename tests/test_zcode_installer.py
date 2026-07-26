from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import installer_orchestration
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.installer import (
    _bundle_files,
    _native_command_plan,
    inspect_host_installation,
    install_agent_adapter,
    plan_agent_adapter,
    rollback_agent_adapter,
    toggle_agency,
)
from agency_runtime.core.installer_zcode import (
    ZCODE_EVENTS,
    ZCodeRegistrationError,
    _atomic_json_replace,
    zcode_config_path,
)


@pytest.fixture(scope="module")
def fixed_launcher_paths() -> tuple[str, str]:
    return installer_orchestration._prepare_adapter_launcher_paths()


@pytest.fixture(autouse=True)
def stable_launcher_identity(
    monkeypatch: pytest.MonkeyPatch,
    fixed_launcher_paths: tuple[str, str],
) -> None:
    monkeypatch.setattr(
        installer_orchestration,
        "_prepare_adapter_launcher_paths",
        lambda: fixed_launcher_paths,
    )


def _user_handler() -> dict[str, Any]:
    return {
        "hooks": [
            {
                "type": "process",
                "command": str(Path(sys.executable).resolve()),
                "args": ["-c", "pass"],
                "enabled": True,
                "timeoutMs": 1_000,
            }
        ]
    }


def _seed_zcode(home: Path, *, global_enabled: bool = True) -> Path:
    path = home / ".zcode" / "cli" / "config.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "theme": "user-owned",
                "hooks": {
                    "enabled": global_enabled,
                    "timeoutMs": 12_345,
                    "maxOutputBytes": 98_765,
                    "events": {"SessionStart": [_user_handler()]},
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _agency_registration(config: dict[str, Any], event: str) -> dict[str, Any]:
    matches = [
        registration
        for registration in config["hooks"]["events"][event]
        if any(
            "agency_runtime.cli" in handler.get("args", [])
            for handler in registration.get("hooks", [])
        )
    ]
    assert len(matches) == 1
    return matches[0]


def _install(home: Path) -> dict[str, Any]:
    return install_agent_adapter(
        "zcode",
        AgencyConfig(),
        home_dir=home,
        binary_resolver=lambda _binary: None,
    )


def test_zcode_bundle_is_not_a_marketplace_and_uses_exact_35_contract() -> None:
    files, primary = _bundle_files("zcode", AgencyConfig())

    assert primary == "zcode-hooks.json"
    assert set(files) == {primary}
    assert not any("claude" in path or "plugin.json" in path for path in files)
    payload = json.loads(files[primary])
    hooks = payload["hooks"]
    assert hooks["enabled"] is True
    assert isinstance(hooks["timeoutMs"], int)
    assert set(hooks["events"]) == set(ZCODE_EVENTS)
    for event in ZCODE_EVENTS:
        registration = hooks["events"][event][0]
        handler = registration["hooks"][0]
        assert handler["type"] == "process"
        assert Path(handler["command"]).is_absolute()
        assert handler["enabled"] is True
        index = handler["args"].index("--event")
        assert handler["args"][index + 1] == event
    assert hooks["events"]["PreToolUse"][0]["matcher"] == "Agent"
    for event in ("PermissionRequest", "PostToolUse", "PostToolUseFailure"):
        assert hooks["events"][event][0]["matcher"] == "*"


def test_zcode_plan_contains_config_actions_and_no_plugin_cli(tmp_path: Path) -> None:
    _seed_zcode(tmp_path)

    result = plan_agent_adapter(
        "zcode",
        AgencyConfig(),
        home_dir=tmp_path,
        binary_resolver=lambda _binary: None,
    )

    assert result["ok"] is True
    assert result["commands_will_run"] is False
    assert result["config_mutations_will_run"] is True
    assert result["native_command_plan"] == _native_command_plan(
        "zcode", Path(result["filesystem"]["target"])
    )
    assert [step["name"] for step in result["native_command_plan"]] == [
        "config_merge",
        "config_inventory",
    ]
    assert all("argv" not in step for step in result["native_command_plan"])


def test_zcode_install_preserves_user_config_and_is_byte_idempotent(tmp_path: Path) -> None:
    config_path = _seed_zcode(tmp_path)

    first = _install(tmp_path)
    first_bytes = config_path.read_bytes()
    first_state = (tmp_path / ".agency-runtime" / "zcode-registration.json").read_bytes()
    second = _install(tmp_path)

    assert first["ok"] is True
    assert first["registered"] is True
    assert first["enabled"] is True
    assert first["loaded"] is None
    assert first["maturity"] == "enabled-runtime-unverified"
    assert second["ok"] is True
    assert second["filesystem"]["unchanged"] is True
    assert config_path.read_bytes() == first_bytes
    assert (tmp_path / ".agency-runtime" / "zcode-registration.json").read_bytes() == first_state
    config = json.loads(first_bytes)
    assert config["theme"] == "user-owned"
    assert config["hooks"]["timeoutMs"] == 12_345
    assert config["hooks"]["maxOutputBytes"] == 98_765
    assert config["hooks"]["events"]["SessionStart"][0] == _user_handler()
    assert set(config["hooks"]["events"]).issuperset(ZCODE_EVENTS)
    for event in ZCODE_EVENTS:
        _agency_registration(config, event)


def test_zcode_install_uses_frozen_launcher_identity(tmp_path: Path) -> None:
    _seed_zcode(tmp_path)

    result = _install(tmp_path)

    manifest = json.loads(
        (Path(result["target"]) / ".agency-runtime-launcher.json").read_text(encoding="utf-8")
    )
    artifacts = manifest["artifacts"]
    config = json.loads(zcode_config_path(home_dir=tmp_path).read_text(encoding="utf-8"))
    handler = _agency_registration(config, "SessionStart")["hooks"][0]
    assert handler["command"] == artifacts[0]["lexical_path"]
    assert handler["args"][:4] == [
        "-I",
        "-S",
        artifacts[1]["lexical_path"],
        "agency_runtime.cli",
    ]


def test_zcode_global_disabled_is_preserved_and_reported(tmp_path: Path) -> None:
    config_path = _seed_zcode(tmp_path, global_enabled=False)

    result = _install(tmp_path)
    inspection = inspect_host_installation(
        "zcode",
        home_dir=tmp_path,
        binary_resolver=lambda _binary: None,
    )
    before_enable = config_path.read_bytes()
    refused = toggle_agency("zcode", True, home_dir=tmp_path)

    assert result["ok"] is True
    assert result["registered"] is True
    assert result["enabled"] is False
    assert result["maturity"] == "registered-disabled"
    assert inspection["registered"] is True
    assert inspection["enabled"] is False
    assert inspection["maturity"] == "registered-disabled"
    assert refused["ok"] is False
    assert "refusing to enable unrelated user hooks" in refused["error"]
    assert config_path.read_bytes() == before_enable


def test_zcode_toggle_changes_only_agency_handlers(tmp_path: Path) -> None:
    config_path = _seed_zcode(tmp_path)
    assert _install(tmp_path)["ok"] is True

    disabled = toggle_agency("zcode", False, home_dir=tmp_path)
    disabled_config = json.loads(config_path.read_text(encoding="utf-8"))
    enabled = toggle_agency("zcode", True, home_dir=tmp_path)
    enabled_config = json.loads(config_path.read_text(encoding="utf-8"))

    assert disabled["ok"] is True
    assert disabled["enabled"] is False
    assert enabled["ok"] is True
    assert enabled["enabled"] is True
    assert disabled_config["hooks"]["enabled"] is True
    assert disabled_config["hooks"]["events"]["SessionStart"][0] == _user_handler()
    assert enabled_config["hooks"]["events"]["SessionStart"][0] == _user_handler()
    for event in ZCODE_EVENTS:
        disabled_registration = _agency_registration(disabled_config, event)
        enabled_registration = _agency_registration(enabled_config, event)
        assert disabled_registration["hooks"][0]["enabled"] is False
        assert enabled_registration["hooks"][0]["enabled"] is True


def test_zcode_owned_handler_drift_refuses_install_toggle_and_status_truth(
    tmp_path: Path,
) -> None:
    config_path = _seed_zcode(tmp_path)
    assert _install(tmp_path)["ok"] is True
    drifted = json.loads(config_path.read_text(encoding="utf-8"))
    _agency_registration(drifted, "Stop")["hooks"][0]["statusMessage"] = "tampered"
    config_path.write_text(
        json.dumps(drifted, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    drift_bytes = config_path.read_bytes()

    reinstall = _install(tmp_path)
    toggle = toggle_agency("zcode", False, home_dir=tmp_path)
    inspection = inspect_host_installation(
        "zcode",
        home_dir=tmp_path,
        binary_resolver=lambda _binary: None,
    )

    assert reinstall["ok"] is False
    assert reinstall["failed_step"] == "config_drift"
    assert toggle["ok"] is False
    assert inspection["registered"] is False
    assert inspection["maturity"] == "staged-not-registered"
    assert "zcode-config-drift:True" in inspection["evidence"]
    assert config_path.read_bytes() == drift_bytes


def test_zcode_status_never_calls_a_plugin_cli(tmp_path: Path) -> None:
    _seed_zcode(tmp_path)
    assert _install(tmp_path)["ok"] is True

    def forbidden_runner(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("ZCode status must not execute a host command")

    inspection = inspect_host_installation(
        "zcode",
        home_dir=tmp_path,
        binary_resolver=lambda _binary: "zcode",
        command_runner=forbidden_runner,
    )

    assert inspection["registered"] is True
    assert inspection["enabled"] is True
    assert inspection["inventory_error"] is None
    assert any(item == "zcode-config:registered" for item in inspection["evidence"])


def test_zcode_atomic_config_write_refuses_concurrent_change(tmp_path: Path) -> None:
    config_path = _seed_zcode(tmp_path)
    expected = config_path.read_bytes()
    concurrent = json.loads(expected)
    concurrent["theme"] = "changed-concurrently"
    config_path.write_text(
        json.dumps(concurrent, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    observed = config_path.read_bytes()

    with pytest.raises(ZCodeRegistrationError, match="changed concurrently"):
        _atomic_json_replace(
            config_path,
            {"theme": "would-clobber"},
            expected=expected,
            product_owned_parent=False,
            label="ZCode config",
        )

    assert config_path.read_bytes() == observed


def test_zcode_rollback_reconciles_retained_fragment_without_clobbering_user_config(
    tmp_path: Path,
) -> None:
    config_path = _seed_zcode(tmp_path)
    first = _install(tmp_path)
    assert first["ok"] is True
    target = Path(first["target"])
    fragment_path = target / "zcode-hooks.json"
    historical = json.loads(fragment_path.read_text(encoding="utf-8"))
    historical["hooks"]["events"]["Stop"][0]["hooks"][0]["statusMessage"] = (
        "Historical Agency stop check"
    )
    fragment_path.write_text(
        json.dumps(historical, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    refreshed = _install(tmp_path)
    backup = Path(refreshed["backup_path"])
    rolled_back = rollback_agent_adapter(
        "zcode",
        home_dir=tmp_path,
        backup_path=backup,
        binary_resolver=lambda _binary: None,
    )

    assert refreshed["ok"] is True
    assert rolled_back["ok"] is True
    assert rolled_back["native_refreshed"] is True
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["theme"] == "user-owned"
    assert config["hooks"]["events"]["SessionStart"][0] == _user_handler()
    stop = _agency_registration(config, "Stop")
    assert stop["hooks"][0]["statusMessage"] == "Historical Agency stop check"
