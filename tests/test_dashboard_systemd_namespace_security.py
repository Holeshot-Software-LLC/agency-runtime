"""Adversarial XDG namespace tests for the Linux dashboard service."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import dashboard_service_core as core
from agency_runtime.core import dashboard_service_inspection as inspection
from agency_runtime.core import dashboard_service_install as install
from agency_runtime.core import dashboard_service_manifest as manifest
from agency_runtime.core import dashboard_service_systemd as systemd
from agency_runtime.core.configuration_contracts import ConfigurationError


def _linux_context(tmp_path: Path) -> core._Context:
    ctx = core._context(
        home_dir=tmp_path,
        platform_name="linux",
        config_path=tmp_path / "agency.yaml",
        python_executable=sys.executable,
    )
    assert ctx is not None and ctx.unit_path is not None and ctx.unit_root is not None
    return ctx


def test_context_binds_absolute_xdg_root_to_unit_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    xdg_root = tmp_path / "custom-xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_root))

    ctx = core._context(
        home_dir=None,
        platform_name="linux",
        config_path=tmp_path / "agency.yaml",
        python_executable=sys.executable,
    )

    assert ctx is not None
    assert ctx.unit_root == Path(os.path.abspath(xdg_root))
    assert ctx.unit_path == ctx.unit_root / "systemd" / "user" / core.SYSTEMD_UNIT_NAME


def test_systemd_unit_must_remain_inside_frozen_xdg_root(tmp_path: Path) -> None:
    ctx = _linux_context(tmp_path)
    escaped = replace(ctx, unit_root=tmp_path / "other-root")

    with pytest.raises(ConfigurationError, match="escaped"):
        systemd._systemd_unit_root(escaped)


def test_systemd_helpers_reject_context_without_unit_path(tmp_path: Path) -> None:
    ctx = replace(_linux_context(tmp_path), unit_path=None)

    with pytest.raises(RuntimeError, match="no unit path"):
        systemd._systemd_unit_root(ctx)
    with pytest.raises(RuntimeError, match="no unit path"):
        systemd._read_systemd_unit(ctx)


def test_systemd_unit_read_rechecks_namespace_after_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _linux_context(tmp_path)
    checks: list[Path] = []
    monkeypatch.setattr(
        systemd,
        "_assert_systemd_unit_namespace",
        lambda candidate: checks.append(candidate.unit_path),
    )
    monkeypatch.setattr(systemd, "_read_service_file", lambda _path: b"unit")

    assert systemd._read_systemd_unit(ctx) == b"unit"
    assert checks == [ctx.unit_path, ctx.unit_path]


def test_systemd_namespace_uses_shared_config_mutation_predicate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _linux_context(tmp_path)
    checked: list[Path] = []
    monkeypatch.setattr(systemd, "assert_config_namespace", checked.append)

    systemd._assert_systemd_unit_namespace(ctx)

    assert checked == [ctx.unit_path]


@pytest.mark.parametrize(
    "release",
    (
        "5.15.153.1-microsoft-standard-WSL2",
        "4.4.0-19041-Microsoft",
    ),
)
def test_wsl_detection_accepts_bounded_kernel_markers(release: str) -> None:
    assert systemd._is_wsl_kernel(release_reader=lambda: release)


@pytest.mark.parametrize(
    "release",
    (
        "6.8.0-1024-generic",
        "",
        "x" * 4097,
        None,
    ),
)
def test_wsl_detection_fails_secure_without_bounded_kernel_evidence(
    release: object,
) -> None:
    assert not systemd._is_wsl_kernel(release_reader=lambda: release)  # type: ignore[return-value]


@pytest.mark.parametrize("error", (OSError("blocked"), RuntimeError("failed"), ValueError("bad")))
def test_wsl_detection_fails_secure_when_kernel_evidence_is_unreadable(
    error: Exception,
) -> None:
    def fail() -> str:
        raise error

    assert not systemd._is_wsl_kernel(release_reader=fail)


def test_wsl_systemd_unit_omits_only_private_tmp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(systemd, "_is_wsl_kernel", lambda: True)

    content = systemd._unit_content(_linux_context(tmp_path))

    assert "PrivateTmp=" not in content
    assert "NoNewPrivileges=true" in content
    assert "UMask=0077" in content
    assert "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6" in content


def test_normal_linux_systemd_unit_retains_private_tmp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(systemd, "_is_wsl_kernel", lambda: False)

    assert "PrivateTmp=true" in systemd._unit_content(_linux_context(tmp_path))


def test_trusted_parent_creation_rejects_namespace_before_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unit = tmp_path / "xdg" / "systemd" / "user" / core.SYSTEMD_UNIT_NAME
    created: list[Path] = []
    monkeypatch.setattr(
        manifest,
        "assert_config_namespace",
        lambda _path: (_ for _ in ()).throw(
            ConfigurationError("configuration parent permits cross-account path substitution")
        ),
    )
    monkeypatch.setattr(
        "agency_runtime.core.private_paths.ensure_private_directory",
        lambda path: created.append(path) or path,
    )

    with pytest.raises(ConfigurationError, match="cross-account"):
        manifest._prepare_private_parent(unit, trusted_root=tmp_path / "xdg")
    assert created == []


def test_namespace_bound_unlink_rechecks_immediately_before_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "unit.service"
    path.write_text("unit", encoding="utf-8")
    checks: list[Path] = []
    monkeypatch.setattr(manifest, "assert_config_namespace", checks.append)

    assert manifest._safe_unlink(path, trusted_root=tmp_path)
    assert checks == [path, path]
    assert not path.exists()


def test_linux_inspection_converts_untrusted_namespace_to_indeterminate_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _linux_context(tmp_path)
    monkeypatch.setattr(inspection, "_path_present", lambda _path: True)
    monkeypatch.setattr(
        inspection,
        "_read_systemd_unit",
        lambda _ctx: (_ for _ in ()).throw(
            ConfigurationError("configuration parent permits cross-account path substitution")
        ),
    )

    snapshot = inspection._read_linux_unit(ctx)

    assert snapshot.exists
    assert not snapshot.readable


def test_linux_inspection_rejects_unsafe_namespace_even_when_unit_is_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _linux_context(tmp_path)
    monkeypatch.setattr(inspection, "_path_present", lambda _path: False)
    monkeypatch.setattr(
        inspection,
        "_assert_systemd_unit_namespace",
        lambda _ctx: (_ for _ in ()).throw(
            ConfigurationError("configuration parent permits cross-account path substitution")
        ),
    )

    snapshot = inspection._read_linux_unit(ctx)

    assert not snapshot.exists
    assert not snapshot.readable


def test_linux_install_passes_frozen_xdg_root_to_atomic_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _linux_context(tmp_path)
    writes: list[tuple[Path, Path | None]] = []
    monkeypatch.setattr(install, "_revalidate_dashboard_launcher", lambda _value: None)
    monkeypatch.setattr(install, "_path_present", lambda _path: False)
    monkeypatch.setattr(install, "_read_manifest_bytes", lambda _ctx: b"manifest")
    monkeypatch.setattr(
        install,
        "_atomic_write",
        lambda path, _content, **kwargs: writes.append((path, kwargs.get("trusted_root"))),
    )
    monkeypatch.setattr(install, "_write_manifest", lambda _ctx: False)
    monkeypatch.setattr(install, "_assert_systemd_files", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        install,
        "_run",
        lambda argv, **_kwargs: core._CommandResult(tuple(argv), 0, "", ""),
    )

    result = install._install_linux(
        ctx,
        {"enabled": False, "active": False, "reachable": None},
        command_runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
        readiness_probe=lambda: True,
    )

    assert result["ok"] is True
    assert writes == [(ctx.unit_path, ctx.unit_root)]


def test_manager_environment_parser_returns_names_without_values() -> None:
    config = SimpleNamespace(
        judge=SimpleNamespace(api_key_env="CUSTOM_JUDGE_KEY"),
        providers=(),
        adapters=SimpleNamespace(
            litellm=None,
            hermes=None,
            openclaw=None,
            codex=None,
            claude=None,
        ),
    )

    names = core.dashboard_service_manager_environment_overrides(
        config,
        "AGENCY_DB_PATH=private.db\n"
        "CUSTOM_JUDGE_KEY=secret-value\n"
        "AGENCY_CONFIG_PATH=durable.yaml\n"
        "MALFORMED\n",
    )

    assert names == ("AGENCY_DB_PATH", "CUSTOM_JUDGE_KEY")


def test_failed_manager_environment_probe_redacts_both_streams_from_plan(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".agency-runtime" / "agency.yaml"
    config_path.parent.mkdir()
    config_path.write_text("profile: standard\n", encoding="utf-8")

    def runner(argv: list[str], **_kwargs: object) -> dict[str, object]:
        assert argv == ["systemctl", "--user", "show-environment"]
        return {
            "returncode": 1,
            "stdout": "AGENCY_DB_PATH=stdout-secret-value\nUNRELATED=also-secret\n",
            "stderr": "LITELLM_API_KEY=stderr-secret-value\nprivate failure detail\n",
        }

    result = inspection.plan_dashboard_service(
        home_dir=tmp_path,
        platform_name="linux",
        config_path=config_path,
        python_executable=sys.executable,
        command_runner=runner,
    )

    assert result["manager_probe"] == {
        "command": ["systemctl", "--user", "show-environment"],
        "returncode": 1,
        "ok": False,
        "error": "systemd user manager environment probe failed; output redacted",
        "reported_environment_names": ["AGENCY_DB_PATH", "LITELLM_API_KEY"],
    }
    encoded = json.dumps(result)
    for sensitive in (
        "stdout-secret-value",
        "stderr-secret-value",
        "also-secret",
        "private failure detail",
    ):
        assert sensitive not in encoded


@pytest.mark.parametrize("operation", ["plan", "install", "inspect"])
def test_public_service_mutation_rejects_manager_only_runtime_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    home = tmp_path / operation
    home.mkdir()
    config_path = home / ".agency-runtime" / "agency.yaml"
    config_path.parent.mkdir()
    config_path.write_text("profile: standard\n", encoding="utf-8")
    commands: list[list[str]] = []
    monkeypatch.setattr(install, "_validate_dashboard_launcher", lambda value: value)
    monkeypatch.setattr(install, "_revalidate_dashboard_launcher", lambda _value: None)
    monkeypatch.setattr(inspection, "_validate_dashboard_launcher", lambda value: value)

    def runner(argv: list[str], **_kwargs: object) -> dict[str, object]:
        commands.append(argv)
        assert argv[-1] == "show-environment"
        return {
            "returncode": 0,
            "stdout": "AGENCY_DB_PATH=manager-only-private-value\n",
        }

    function = {
        "plan": inspection.plan_dashboard_service,
        "install": install.install_dashboard_service,
        "inspect": inspection.inspect_dashboard_service,
    }[operation]
    result = function(
        home_dir=home,
        platform_name="linux",
        config_path=config_path,
        python_executable=sys.executable,
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["changed"] is False
    assert result["commands"] == []
    assert result["non_durable_manager_environment_overrides"] == ["AGENCY_DB_PATH"]
    assert "manager-only-private-value" not in json.dumps(result)
    assert commands == [["systemctl", "--user", "show-environment"]]
