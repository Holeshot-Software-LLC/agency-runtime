"""Dedicated-container managed Codex hook policy coverage."""

from __future__ import annotations

from pathlib import Path

import tomllib

from agency_runtime.core import codex_managed_policy, installer_inventory
from agency_runtime.core.codex_managed_policy import (
    MANAGED_POLICY_INSPECTION_SCHEMA,
    MANAGED_POLICY_SCHEMA,
    inspect_managed_codex_policy,
    install_managed_codex_policy,
    plan_managed_codex_policy,
)
from agency_runtime.core.config import load_config
from agency_runtime.core.installer_contracts import CODEX_HOOK_EVENTS


def _config(tmp_path: Path):
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    return path, load_config(path, reload=True)


def _payload(document: str) -> str:
    return document.split("\n", 2)[2]


def test_managed_codex_policy_installs_exact_idempotent_system_contract(tmp_path: Path) -> None:
    config_path, cfg = _config(tmp_path)
    requirements = tmp_path / "system" / "requirements.toml"
    posix_dir = tmp_path / "system" / "hooks"
    windows_dir = tmp_path / "windows" / "hooks"

    result = install_managed_codex_policy(
        cfg,
        config_path=config_path,
        requirements_path=requirements,
        posix_managed_dir=posix_dir,
        windows_managed_dir=windows_dir,
        platform_system="linux",
        launcher_preparer=lambda: ("/opt/agency/python", "/opt/agency/_bootstrap.py"),
        control_path=tmp_path / "runtime-control.json",
    )

    assert result["ok"] is True
    assert result["complete"] is True
    assert result["changed"] is True
    assert result["status"] == "installed"
    assert result["schema_version"] == MANAGED_POLICY_SCHEMA
    assert result["trust_mode"] == "managed_policy"
    assert result["allow_managed_hooks_only"] is True
    assert result["hook_events"] == list(CODEX_HOOK_EVENTS)
    parsed = tomllib.loads(_payload(requirements.read_text(encoding="utf-8")))
    assert parsed["allow_managed_hooks_only"] is True
    assert parsed["features"]["hooks"] is True
    assert parsed["hooks"]["managed_dir"] == str(posix_dir)
    assert parsed["hooks"]["windows_managed_dir"] == str(windows_dir)
    assert tuple(parsed["hooks"][event][0]["hooks"][0]["type"] for event in CODEX_HOOK_EVENTS) == (
        "command",
    ) * len(CODEX_HOOK_EVENTS)
    assert parsed["hooks"]["UserPromptSubmit"][0]["hooks"][0]["additionalContextLimit"] == 0
    relay = (posix_dir / "agency-runtime-hook.py").read_text(encoding="utf-8")
    namespace = {"__name__": "managed_relay_test"}
    exec(compile(_payload(relay), "managed-relay", "exec"), namespace)
    assert namespace["_BINDING"]["config"] == str(config_path)
    assert "/opt/agency/_bootstrap.py" in relay
    inspected = inspect_managed_codex_policy(
        requirements_path=requirements,
        posix_managed_dir=posix_dir,
        windows_managed_dir=windows_dir,
        platform_system="linux",
    )
    assert inspected["schema_version"] == MANAGED_POLICY_INSPECTION_SCHEMA
    assert inspected["status"] == "current"
    assert inspected["current"] is True
    assert inspected["trust_mode"] == "managed_policy"
    assert inspected["config_path"] == str(config_path)
    assert inspected["hook_events"] == list(CODEX_HOOK_EVENTS)
    assert len(inspected["requirements_digest"]) == 64
    assert len(inspected["relay_digest"]) == 64

    repeated = install_managed_codex_policy(
        cfg,
        config_path=config_path,
        requirements_path=requirements,
        posix_managed_dir=posix_dir,
        windows_managed_dir=windows_dir,
        platform_system="linux",
        launcher_preparer=lambda: ("/opt/agency/python", "/opt/agency/_bootstrap.py"),
        control_path=tmp_path / "runtime-control.json",
    )
    assert repeated["ok"] is True
    assert repeated["changed"] is False
    assert repeated["status"] == "current"


def test_managed_codex_policy_refuses_foreign_system_policy_without_writes(
    tmp_path: Path,
) -> None:
    config_path, cfg = _config(tmp_path)
    requirements = tmp_path / "system" / "requirements.toml"
    requirements.parent.mkdir()
    requirements.write_text("[features]\nhooks = false\n", encoding="utf-8")
    posix_dir = tmp_path / "system" / "hooks"

    plan = plan_managed_codex_policy(
        cfg,
        config_path=config_path,
        requirements_path=requirements,
        posix_managed_dir=posix_dir,
        windows_managed_dir=tmp_path / "windows-hooks",
        platform_system="linux",
    )
    assert plan["ok"] is False
    assert plan["status"] == "refused"
    assert "not owned by Agency Runtime" in plan["error"]

    result = install_managed_codex_policy(
        cfg,
        config_path=config_path,
        requirements_path=requirements,
        posix_managed_dir=posix_dir,
        windows_managed_dir=tmp_path / "windows-hooks",
        platform_system="linux",
        launcher_preparer=lambda: (_ for _ in ()).throw(AssertionError("must not prepare")),
    )
    assert result["ok"] is False
    assert requirements.read_text(encoding="utf-8") == "[features]\nhooks = false\n"
    assert not posix_dir.exists()


def test_managed_codex_policy_refuses_foreign_relay(tmp_path: Path) -> None:
    config_path, cfg = _config(tmp_path)
    managed_dir = tmp_path / "hooks"
    managed_dir.mkdir()
    relay = managed_dir / "agency-runtime-hook.py"
    relay.write_text("raise SystemExit('foreign')\n", encoding="utf-8")

    result = install_managed_codex_policy(
        cfg,
        config_path=config_path,
        requirements_path=tmp_path / "requirements.toml",
        posix_managed_dir=managed_dir,
        windows_managed_dir=tmp_path / "windows-hooks",
        platform_system="linux",
        launcher_preparer=lambda: (_ for _ in ()).throw(AssertionError("must not prepare")),
    )
    assert result["ok"] is False
    assert "not owned by Agency Runtime" in result["error"]
    assert relay.read_text(encoding="utf-8") == "raise SystemExit('foreign')\n"


def test_managed_codex_policy_reports_partial_write_truthfully(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path, cfg = _config(tmp_path)
    requirements = tmp_path / "system" / "requirements.toml"
    managed_dir = tmp_path / "system" / "hooks"
    real_atomic_write = codex_managed_policy.atomic_write_text
    writes = 0

    def _fail_second_write(path: Path, content: str) -> None:
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("simulated system-policy write failure")
        real_atomic_write(path, content)

    monkeypatch.setattr(codex_managed_policy, "atomic_write_text", _fail_second_write)
    result = install_managed_codex_policy(
        cfg,
        config_path=config_path,
        requirements_path=requirements,
        posix_managed_dir=managed_dir,
        windows_managed_dir=tmp_path / "windows-hooks",
        platform_system="linux",
        launcher_preparer=lambda: ("/opt/agency/python", "/opt/agency/_bootstrap.py"),
    )

    assert result["ok"] is False
    assert result["complete"] is False
    assert result["changed"] is True
    assert result["status"] == "failed"
    assert "simulated system-policy write failure" in result["error"]
    assert (managed_dir / "agency-runtime-hook.py").is_file()
    assert not requirements.exists()


def test_managed_codex_policy_inspection_distinguishes_absent_foreign_and_drifted(
    tmp_path: Path,
) -> None:
    config_path, cfg = _config(tmp_path)
    requirements = tmp_path / "system" / "requirements.toml"
    managed_dir = tmp_path / "system" / "hooks"
    windows_dir = tmp_path / "windows-hooks"
    absent = inspect_managed_codex_policy(
        requirements_path=requirements,
        posix_managed_dir=managed_dir,
        windows_managed_dir=windows_dir,
        platform_system="linux",
    )
    assert absent["status"] == "absent"
    assert absent["current"] is False

    requirements.parent.mkdir(parents=True)
    requirements.write_text("[features]\nhooks = false\n", encoding="utf-8")
    foreign = inspect_managed_codex_policy(
        requirements_path=requirements,
        posix_managed_dir=managed_dir,
        windows_managed_dir=windows_dir,
        platform_system="linux",
    )
    assert foreign["status"] == "foreign_or_modified"
    assert foreign["drift_reasons"] == ["ownership_or_file_trust"]

    requirements.unlink()
    installed = install_managed_codex_policy(
        cfg,
        config_path=config_path,
        requirements_path=requirements,
        posix_managed_dir=managed_dir,
        windows_managed_dir=windows_dir,
        platform_system="linux",
        launcher_preparer=lambda: ("/opt/agency/python", "/opt/agency/_bootstrap.py"),
    )
    assert installed["ok"] is True
    payload = _payload(requirements.read_text(encoding="utf-8")).replace(
        "hooks = true",
        "hooks = false",
        1,
    )
    codex_managed_policy.atomic_write_text(
        requirements,
        codex_managed_policy._owned_document("codex-requirements", payload),
    )
    drifted = inspect_managed_codex_policy(
        requirements_path=requirements,
        posix_managed_dir=managed_dir,
        windows_managed_dir=windows_dir,
        platform_system="linux",
    )
    assert drifted["status"] == "drifted"
    assert "hooks_feature" in drifted["drift_reasons"]
    assert drifted["trust_mode"] is None


def test_host_projection_reports_managed_authority_and_invalidates_drifted_proof(
    monkeypatch,
) -> None:
    current = {
        "canary": True,
        "canary_attestation_status": "verified",
        "canary_stale_reasons": [],
        "canary_attestation": {"profile_scope": "current-profile"},
        "maturity": "runtime-verified",
        "hook_trust_status": "trusted",
        "evidence": [],
    }
    monkeypatch.setattr(
        codex_managed_policy,
        "inspect_managed_codex_policy",
        lambda: {
            "status": "current",
            "current": True,
            "trust_mode": "managed_policy",
            "hook_events": list(CODEX_HOOK_EVENTS),
        },
    )
    installer_inventory._apply_codex_managed_policy_projection(current)
    assert current["trust_mode"] == "managed_policy"
    assert current["hook_trust_status"] == "managed"
    assert current["hook_trust_surface"] == "codex-system-policy"
    assert current["canary"] is True

    drifted = {
        **current,
        "canary": True,
        "canary_attestation_status": "verified",
        "canary_stale_reasons": [],
    }
    monkeypatch.setattr(
        codex_managed_policy,
        "inspect_managed_codex_policy",
        lambda: {
            "status": "drifted",
            "current": False,
            "trust_mode": None,
            "drift_reasons": ["hooks_feature"],
        },
    )
    installer_inventory._apply_codex_managed_policy_projection(drifted)
    assert drifted["canary"] is None
    assert drifted["canary_attestation_status"] == "stale"
    assert "managed_hook_policy" in drifted["canary_stale_reasons"]
    assert drifted["hook_trust_status"] == "modified"
    assert drifted["maturity"] == "activation-required"
