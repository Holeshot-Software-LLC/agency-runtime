"""AR-185 exact Codex activation-verification authority and proof contract."""

from __future__ import annotations

import copy
import io
import json
import os
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters import hooks
from agency_runtime.cli import install_commands
from agency_runtime.cli import main as cli_main
from agency_runtime.core import canary_proof, preflight
from agency_runtime.core.activation_canary_contract import (
    CODEX_ACTIVATION_CANARY_WORK_UNIT,
)
from agency_runtime.core.canary_backends import SafeCodexCanaryBackend
from agency_runtime.core.codex_activation_verification import (
    CODEX_ACTIVATION_QUERY_HASH_ENV,
    is_exact_codex_activation_verification,
    restricted_codex_activation_query_hash,
)
from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.installer_contracts import (
    CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
    CODEX_HOOK_EVENTS,
)
from agency_runtime.core.native_child_staffing import NativeChildStaffingResult
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.unit_assignment import work_unit_id_from_text


def _identity() -> dict[str, Any]:
    return {
        "host": "codex",
        "current_native_root": True,
        "effective_enabled": True,
        "enabled": True,
        "executable_discovered": True,
        "launcher_artifacts_current": True,
        "marketplace_registered": True,
        "registered": True,
        "staged": True,
        "host_version": "codex-cli 0.145.0",
        "install_id": "install-1",
        "bundle_digest": "a" * 64,
        "managed_plugin_version": "0.1.0",
        "canary": None,
        "canary_attestation_status": "absent",
        "canary_attestation": None,
        "hook_trust_status": "unverified",
    }


def _attestation(*, passed_at: str | None = None) -> dict[str, str]:
    sampled_at = passed_at or datetime.now(timezone.utc).isoformat()
    return {
        "host": "codex",
        "proof_contract": CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
        "proof_digest": "b" * 64,
        "profile_scope": "current-profile",
        "platform_system": "Windows",
        "platform_release": "11",
        "platform_machine": "AMD64",
        "host_version": "codex-cli 0.145.0",
        "plugin_version": "0.1.0",
        "install_id": "install-1",
        "bundle_digest": "a" * 64,
        "trace_id": "11111111-1111-4111-8111-111111111111",
        "passed_at": sampled_at,
    }


def _fresh_report() -> dict[str, Any]:
    sampled_at = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": "agency.host_canary.v1",
        "sampled_at": sampled_at,
        "host": "codex",
        "mode": "agency",
        "profile_scope": "current-profile",
        "live_attempted": True,
        "canary_passed": True,
        "attestation_persisted": True,
        "unmet_prerequisites": [],
        "attestation": _attestation(passed_at=sampled_at),
    }


def _final_inspection(attestation: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        **_identity(),
        "canary": True,
        "canary_attestation_status": "verified",
        "canary_attestation": attestation or _attestation(),
        "hook_trust_status": "trusted",
    }


def _forbidden(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("verification-only path crossed a forbidden mutation boundary")


def _dependencies(
    *,
    inspections: list[Any],
    canary_runner,
    emitted: list[dict[str, Any]],
) -> install_commands.InstallDependencies:
    def inspect(_host: str) -> dict[str, Any]:
        value = inspections.pop(0)
        return value() if callable(value) else value

    return install_commands.InstallDependencies(
        load_config=_forbidden,
        store_factory=_forbidden,
        emit_json=emitted.append,
        readiness_probe=_forbidden,
        canary_runner=canary_runner,
        host_inspector=inspect,
        prepared_codex_installer=_forbidden,
    )


def test_exact_cli_main_verification_reaches_only_one_bound_canary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agency_runtime.core.dashboard_service as dashboard_service
    import agency_runtime.core.installer as installer

    emitted: list[dict[str, Any]] = []
    canary_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    fresh: dict[str, Any] = {}

    def run_canary(*args: Any, **kwargs: Any) -> dict[str, Any]:
        canary_calls.append((args, kwargs))
        fresh.update(_fresh_report())
        return fresh

    dependencies = _dependencies(
        inspections=[_identity(), lambda: _final_inspection(fresh["attestation"])],
        canary_runner=run_canary,
        emitted=emitted,
    )
    monkeypatch.setattr(cli_main, "_install_dependencies", lambda: dependencies)
    monkeypatch.setattr(install_commands, "_materialize_install_controls", _forbidden)
    monkeypatch.setattr(install_commands, "_run_prepared_codex_refresh", _forbidden)
    for name in (
        "detect_installed_agents",
        "install_agent_adapter",
        "plan_agent_adapter",
        "rollback_agent_adapter",
        "seed_starter_roster",
    ):
        monkeypatch.setattr(installer, name, _forbidden)
    monkeypatch.setattr(dashboard_service, "install_dashboard_service", _forbidden)
    monkeypatch.setattr(dashboard_service, "plan_dashboard_service", _forbidden)

    assert (
        cli_main.main(
            [
                "install",
                "--agent",
                "codex",
                "--verify-activation",
                "--activation-timeout",
                "42",
                "--json",
            ]
        )
        == 0
    )
    assert canary_calls == [
        (
            ("codex",),
            {
                "execute": True,
                "confirm": "RUN LIVE codex CURRENT-PROFILE CANARY",
                "timeout": 42.0,
                "mode": "agency",
                "profile_scope": "current-profile",
                "require_existing_store": True,
            },
        )
    ]
    assert emitted[0]["ok"] is True
    assert emitted[0]["installation_attempted"] is False
    assert "Codex adapter and trust store" in emitted[0]["untouched"]
    assert emitted[0]["hosts"][0]["activation"]["fresh_attestation"] == fresh["attestation"]


@pytest.mark.parametrize(
    "argv",
    [
        ["install", "--all", "--verify-activation"],
        ["install", "--agent", "claude", "--verify-activation"],
        ["install", "--agent", "codex", "--verify-activation", "--profile", "standard"],
        ["install", "--agent", "codex", "--verify-activation", "--no-dashboard"],
        ["install", "--agent", "codex", "--verify-activation", "--activation-timeout", "0"],
        ["install", "--agent", "codex", "--verify-activation", "--activation-timeout", "601"],
        ["install", "--agent", "codex", "--verify-activation", "--activation-timeout", "nan"],
    ],
)
def test_nearby_verification_shapes_fail_the_closed_world_predicate(
    argv: list[str],
) -> None:
    parsed = cli_main.build_parser().parse_args(argv)

    assert is_exact_codex_activation_verification(parsed) is False


def test_future_public_install_flag_fails_the_closed_world_predicate() -> None:
    parsed = cli_main.build_parser().parse_args(
        ["install", "--agent", "codex", "--verify-activation"]
    )
    parsed.future_install_flag = False

    assert is_exact_codex_activation_verification(parsed) is False


def test_future_hidden_install_flag_fails_the_closed_world_predicate() -> None:
    parsed = cli_main.build_parser().parse_args(
        ["install", "--agent", "codex", "--verify-activation"]
    )
    parsed._force_install = True

    assert is_exact_codex_activation_verification(parsed) is False


def test_unpaired_surrogates_fail_closed_without_escaping_projection() -> None:
    invalid = "\ud800"
    identity = _identity()
    identity["install_id"] = invalid
    assert install_commands._codex_activation_identity(identity) is None

    not_before = datetime.now(timezone.utc)
    candidate = _fresh_report()
    candidate["attestation"] = {**candidate["attestation"], "trace_id": invalid}
    expected_identity = {
        field: str(_identity()[field]) for field in install_commands._ACTIVATION_IDENTITY_FIELDS
    }
    assert (
        install_commands._fresh_activation_attestation(
            candidate,
            expected_identity=expected_identity,
            not_before=not_before,
            not_after=datetime.now(timezone.utc),
            prior_attestation=None,
        )
        is None
    )


def test_prepared_refresh_remains_distinct_from_activation_verification() -> None:
    parsed = cli_main.build_parser().parse_args(["install", "--agent", "codex", "--no-dashboard"])

    assert is_exact_codex_activation_verification(parsed) is False


@pytest.mark.parametrize(
    "candidate",
    [
        None,
        "not-a-report",
        {**_fresh_report(), "schema_version": "wrong"},
        {**_fresh_report(), "host": "claude"},
        {**_fresh_report(), "mode": "native-only"},
        {**_fresh_report(), "profile_scope": "isolated-profile"},
        {**_fresh_report(), "live_attempted": False},
        {**_fresh_report(), "canary_passed": False},
        {**_fresh_report(), "attestation_persisted": False},
        {**_fresh_report(), "unmet_prerequisites": ["failed"]},
        {
            **_fresh_report(),
            "attestation": {**_attestation(), "proof_digest": "c" * 63},
        },
        {
            **_fresh_report(),
            "attestation": {**_attestation(), "install_id": "different"},
        },
    ],
)
def test_malformed_fresh_result_cannot_reuse_an_older_verified_attestation(
    candidate: object,
) -> None:
    emitted: list[dict[str, Any]] = []
    dependencies = _dependencies(
        inspections=[_identity(), _final_inspection()],
        canary_runner=lambda *_args, **_kwargs: candidate,
        emitted=emitted,
    )

    assert (
        install_commands._run_codex_activation_verification(
            json_mode=True,
            timeout=1,
            dependencies=dependencies,
        )
        == 1
    )
    assert emitted[0]["ok"] is False
    assert emitted[0]["hosts"][0]["complete"] is False
    assert "fresh_attestation" not in emitted[0]["hosts"][0]["activation"]


def test_final_attestation_must_match_the_fresh_invocation() -> None:
    fresh: dict[str, Any] = {}

    def candidate(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        fresh.update(_fresh_report())
        return fresh

    def final_inspection() -> dict[str, Any]:
        return _final_inspection(
            {
                **fresh["attestation"],
                "trace_id": "22222222-2222-4222-8222-222222222222",
            }
        )

    emitted: list[dict[str, Any]] = []
    dependencies = _dependencies(
        inspections=[_identity(), final_inspection],
        canary_runner=candidate,
        emitted=emitted,
    )

    assert (
        install_commands._run_codex_activation_verification(
            json_mode=True,
            timeout=1,
            dependencies=dependencies,
        )
        == 1
    )
    assert emitted[0]["hosts"][0]["error"].startswith("final Codex inspection")


def test_valid_old_report_and_matching_old_attestation_are_not_fresh() -> None:
    old_sample = "2020-01-01T00:00:00+00:00"
    old_attestation = _attestation(passed_at=old_sample)
    old_report = {
        **_fresh_report(),
        "sampled_at": old_sample,
        "attestation": old_attestation,
    }
    initial = _identity()
    initial["canary_attestation"] = old_attestation
    emitted: list[dict[str, Any]] = []
    dependencies = _dependencies(
        inspections=[initial, _final_inspection(old_attestation)],
        canary_runner=lambda *_args, **_kwargs: old_report,
        emitted=emitted,
    )

    assert (
        install_commands._run_codex_activation_verification(
            json_mode=True,
            timeout=1,
            dependencies=dependencies,
        )
        == 1
    )
    assert emitted[0]["hosts"][0]["activation"]["state"] == "verification_failed"
    assert emitted[0]["hosts"][0]["activation"]["verification_command"].endswith(
        "--verify-activation"
    )
    assert "Codex Desktop" in emitted[0]["hosts"][0]["activation"]["action"]


def test_initial_incomplete_installation_never_calls_canary() -> None:
    initial = _identity()
    initial["enabled"] = False
    emitted: list[dict[str, Any]] = []
    dependencies = _dependencies(
        inspections=[initial],
        canary_runner=_forbidden,
        emitted=emitted,
    )

    assert (
        install_commands._run_codex_activation_verification(
            json_mode=True,
            timeout=1,
            dependencies=dependencies,
        )
        == 1
    )
    assert "no activation canary was attempted" in emitted[0]["hosts"][0]["error"]


def test_canary_exception_is_sanitized_and_followed_by_reinspection() -> None:
    emitted: list[dict[str, Any]] = []

    def fail(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("private-provider-secret")

    dependencies = _dependencies(
        inspections=[_identity(), _final_inspection()],
        canary_runner=fail,
        emitted=emitted,
    )

    assert (
        install_commands._run_codex_activation_verification(
            json_mode=True,
            timeout=1,
            dependencies=dependencies,
        )
        == 1
    )
    assert "private-provider-secret" not in repr(emitted)


def test_existing_current_store_mode_neither_bootstraps_nor_repairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.store import sqlite as sqlite_store

    db_path = Path(os.environ["AGENCY_DB_PATH"])
    assert not db_path.exists()
    with pytest.raises((OSError, RuntimeError)):
        Store(require_existing_current=True)
    assert not db_path.exists()

    Store()

    def unexpected_repair(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("existing-current Store must not repair permissions")

    monkeypatch.setattr(sqlite_store, "_restrict_path_permissions", unexpected_repair)
    existing = Store(require_existing_current=True)
    assert all(not items for items in existing.recent_runtime_activity(limit=1).values())


def test_live_preparation_cannot_bootstrap_the_activation_store() -> None:
    db_path = Path(os.environ["AGENCY_DB_PATH"])

    missing = canary_proof.prepare_live_invocation(
        "codex",
        path=db_path,
        timeout=1,
        native={},
        backend_factory=lambda *_args, **_kwargs: object(),
        profile_scope="current-profile",
        require_existing_store=True,
    )
    assert missing.error == "runtime evidence store is unavailable"
    assert not db_path.exists()

    Store()
    existing = canary_proof.prepare_live_invocation(
        "codex",
        path=db_path,
        timeout=1,
        native={},
        backend_factory=lambda *_args, **_kwargs: object(),
        profile_scope="current-profile",
        require_existing_store=True,
    )
    assert existing.error is None
    assert existing.store is not None


def test_activation_result_projection_does_not_retain_unknown_content() -> None:
    candidate = copy.deepcopy(_fresh_report())
    candidate["private_provider_payload"] = "secret"

    projected = install_commands._activation_verification_projection(candidate)

    assert "private_provider_payload" not in projected
    assert "secret" not in repr(projected)


def test_activation_projection_preserves_only_sanitized_hook_trust_evidence() -> None:
    candidate = copy.deepcopy(_fresh_report())
    events = tuple(event[0].lower() + event[1:] for event in CODEX_HOOK_EVENTS)
    hook_trust = {
        "status": "modified",
        "expected_count": 8,
        "observed_count": 8,
        "trusted_count": 0,
        "managed_count": 0,
        "modified_count": 8,
        "untrusted_count": 0,
        "disabled_count": 0,
        "missing_count": 0,
        "unexpected_count": 0,
        "duplicate_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "events": {
            event: {
                "enabled": True,
                "trustStatus": "modified",
                "currentHash": "sha256:" + "a" * 64,
            }
            for event in events
        },
    }
    candidate["invocation"] = {
        "failure_reason": "codex_hook_trust_not_ready",
        "model_invocation_attempted": False,
        "hook_trust": hook_trust,
        "private_provider_payload": "secret",
    }

    projected = install_commands._activation_verification_projection(candidate)

    assert projected["invocation"] == {
        "failure_reason": "codex_hook_trust_not_ready",
        "model_invocation_attempted": False,
        "hook_trust": hook_trust,
    }
    assert "secret" not in repr(projected)


def test_activation_projection_preserves_timeout_code_but_not_private_reason_text() -> None:
    candidate = copy.deepcopy(_fresh_report())
    candidate["invocation"] = {
        "failure_reason": "codex_exec_timed_out",
        "private_provider_payload": "private-provider-secret",
    }

    projected = install_commands._activation_verification_projection(candidate)

    assert projected["invocation"] == {"failure_reason": "codex_exec_timed_out"}
    assert "private-provider-secret" not in repr(projected)

    candidate["invocation"] = {"failure_reason": "private-provider-secret"}
    projected = install_commands._activation_verification_projection(candidate)
    assert "invocation" not in projected
    assert "private-provider-secret" not in repr(projected)


def test_activation_projection_rejects_malformed_invocation_fields() -> None:
    candidate = copy.deepcopy(_fresh_report())
    candidate["invocation"] = {
        "failure_reason": [],
        "model_invocation_attempted": "false",
        "hook_trust": {"status": "trusted", "command": "SECRET_COMMAND"},
    }

    projected = install_commands._activation_verification_projection(candidate)

    assert projected["invocation"]["hook_trust"]["status"] == "error"
    assert "failure_reason" not in projected["invocation"]
    assert "model_invocation_attempted" not in projected["invocation"]
    assert "SECRET" not in repr(projected)


def test_activation_projection_never_retains_malformed_known_field_content() -> None:
    class PrivateValue:
        def __repr__(self) -> str:
            return "private-provider-secret"

    projected = install_commands._activation_verification_projection(
        {
            "schema_version": PrivateValue(),
            "host": "private-provider-secret",
            "mode": [PrivateValue()],
            "profile_scope": {"secret": PrivateValue()},
            "unmet_prerequisites": [PrivateValue()],
        }
    )

    assert "private-provider-secret" not in repr(projected)
    assert projected["unmet_prerequisites"] == [
        "fresh current-profile verification returned an invalid result"
    ]


def test_existing_store_requirement_crosses_current_profile_process_boundary(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []
    owner_home = tmp_path / "owner-home"

    def runner(argv: list[str], **kwargs: Any) -> BoundedProcessResult:
        calls.append({"argv": argv, **kwargs})
        return BoundedProcessResult(1, "", "")

    backend = SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=1,
        marketplace=tmp_path,
        auth_source=owner_home / ".codex" / "auth.json",
        process_runner=runner,
        source_env={"HOME": str(owner_home)},
        profile_scope="current-profile",
        require_existing_store=True,
    )

    backend.execute(task="canary", workdir=str(tmp_path))

    assert calls[0]["env"]["AGENCY_CANARY_REQUIRE_EXISTING_STORE"] == "1"
    assert Path(calls[0]["env"]["AGENCY_CANARY_NATIVE_INSTALL_HOME"]) == owner_home.resolve()
    assert CODEX_ACTIVATION_QUERY_HASH_ENV not in calls[0]["env"]


def test_restricted_activation_query_hash_requires_the_exact_environment() -> None:
    digest = "a" * 64
    restricted = {
        "AGENCY_CANARY_MODE": "1",
        "AGENCY_CANARY_REQUIRE_EXISTING_STORE": "1",
        CODEX_ACTIVATION_QUERY_HASH_ENV: digest,
    }

    assert restricted_codex_activation_query_hash(restricted) == digest
    assert restricted_codex_activation_query_hash({}) == ""
    assert (
        restricted_codex_activation_query_hash(
            {**restricted, CODEX_ACTIVATION_QUERY_HASH_ENV: digest.upper()}
        )
        == ""
    )
    assert (
        restricted_codex_activation_query_hash(
            {**restricted, "AGENCY_CANARY_REQUIRE_EXISTING_STORE": "0"}
        )
        == ""
    )


def test_autonomous_current_profile_uses_supported_bypass_without_trust_inspection(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    def runner(argv: list[str], **kwargs: Any) -> BoundedProcessResult:
        calls.append({"argv": argv, **kwargs})
        return BoundedProcessResult(1, "", "")

    backend = SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=1,
        marketplace=tmp_path,
        auth_source=tmp_path / "auth.json",
        process_runner=runner,
        source_env={},
        profile_scope="current-profile",
        require_existing_store=True,
        require_exact_activation_rollout=True,
        hook_trust_inspector=lambda *_args, **_kwargs: pytest.fail(
            "persistent trust must not be inspected in autonomous bypass mode"
        ),
        trust_mode="autonomous_bypass",
    )

    task = "canary"
    result = backend.execute(task=task, workdir=str(tmp_path))

    assert "--dangerously-bypass-hook-trust" in calls[0]["argv"]
    assert result["trust_mode"] == "autonomous_bypass"
    assert result["trust_bypass_used"] is True
    assert result["persistent_trust_changed"] is False


def test_managed_policy_current_profile_uses_normal_invocation_without_plugin_trust_probe(
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    def runner(argv: list[str], **kwargs: Any) -> BoundedProcessResult:
        calls.append({"argv": argv, **kwargs})
        return BoundedProcessResult(1, "", "")

    backend = SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=1,
        marketplace=tmp_path,
        auth_source=tmp_path / "auth.json",
        process_runner=runner,
        source_env={
            "LITELLM_API_KEY": "configured-secret",
            "UNRELATED_TOKEN": "unrelated-secret",
        },
        profile_scope="current-profile",
        require_existing_store=True,
        require_exact_activation_rollout=True,
        hook_trust_inspector=lambda *_args, **_kwargs: pytest.fail(
            "managed hooks are policy-trusted and do not use the plugin trust probe"
        ),
        trust_mode="managed_policy",
        credential_environment_names=("LITELLM_API_KEY",),
    )

    task = "canary"
    result = backend.execute(task=task, workdir=str(tmp_path))

    assert "--dangerously-bypass-hook-trust" not in calls[0]["argv"]
    assert result["trust_mode"] == "managed_policy"
    assert result["trust_bypass_used"] is False
    assert result["persistent_trust_changed"] is False
    assert calls[0]["env"]["LITELLM_API_KEY"] == "configured-secret"
    assert "UNRELATED_TOKEN" not in calls[0]["env"]
    assert (
        calls[0]["env"][CODEX_ACTIVATION_QUERY_HASH_ENV] == sha256(task.encode("utf-8")).hexdigest()
    )


def test_product_rollout_does_not_receive_activation_query_hash(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def runner(argv: list[str], **kwargs: Any) -> BoundedProcessResult:
        calls.append({"argv": argv, **kwargs})
        return BoundedProcessResult(1, "", "")

    backend = SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=1,
        marketplace=tmp_path,
        auth_source=tmp_path / "auth.json",
        process_runner=runner,
        source_env={},
        profile_scope="current-profile",
        require_existing_store=True,
        require_exact_activation_rollout=True,
        rollout_contract="product",
        trust_mode="managed_policy",
        trusted_workdir=str(tmp_path),
    )

    backend.execute(task="ordinary product task", workdir=str(tmp_path))

    assert CODEX_ACTIVATION_QUERY_HASH_ENV not in calls[0]["env"]


@pytest.mark.parametrize(
    "names",
    [
        ("bad-name",),
        ("PATH",),
        ("NODE_OPTIONS",),
        ("AGENCY_CANARY_SECRET",),
        ("DUPLICATE", "DUPLICATE"),
        tuple(f"KEY_{index}" for index in range(257)),
    ],
)
def test_managed_canary_refuses_invalid_credential_environment_names(
    tmp_path: Path,
    names: tuple[str, ...],
) -> None:
    invoked = False

    def runner(*_args: Any, **_kwargs: Any) -> BoundedProcessResult:
        nonlocal invoked
        invoked = True
        return BoundedProcessResult(1, "", "")

    backend = SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=1,
        marketplace=tmp_path,
        auth_source=tmp_path / "auth.json",
        process_runner=runner,
        source_env={"DUPLICATE": "private"},
        profile_scope="current-profile",
        require_existing_store=True,
        require_exact_activation_rollout=True,
        trust_mode="managed_policy",
        credential_environment_names=names,
    )

    with pytest.raises(ValueError, match="credential environment"):
        backend.execute(task="canary", workdir=str(tmp_path))
    assert invoked is False


@pytest.mark.parametrize("value", [["not", "text"], "contains\x00nul", "x" * 65_537])
def test_managed_canary_refuses_invalid_credential_environment_values(
    tmp_path: Path,
    value: object,
) -> None:
    invoked = False

    def runner(*_args: Any, **_kwargs: Any) -> BoundedProcessResult:
        nonlocal invoked
        invoked = True
        return BoundedProcessResult(1, "", "")

    backend = SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=1,
        marketplace=tmp_path,
        auth_source=tmp_path / "auth.json",
        process_runner=runner,
        source_env={"CONFIGURED_KEY": value},  # type: ignore[dict-item]
        profile_scope="current-profile",
        require_existing_store=True,
        require_exact_activation_rollout=True,
        trust_mode="managed_policy",
        credential_environment_names=("CONFIGURED_KEY",),
    )

    with pytest.raises(ValueError, match="credential environment value"):
        backend.execute(task="canary", workdir=str(tmp_path))
    assert invoked is False


def test_current_profile_hook_uses_existing_current_store_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def store_factory(*args: Any, **kwargs: Any) -> Any:
        calls.append({"args": args, "kwargs": kwargs})
        raise RuntimeError("expected boundary stop")

    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(hooks, "Store", store_factory)
    monkeypatch.setattr(
        "agency_runtime.core.runtime_control.read_enforcement_runtime_control",
        lambda: ({"enabled": True}, "test"),
    )
    output = io.BytesIO()

    assert (
        hooks._run_hook_stdio(
            "codex",
            expected_event="UserPromptSubmit",
            input_stream=io.BytesIO(
                b'{"hook_event_name":"UserPromptSubmit","session_id":"session"}'
            ),
            output_stream=output,
            error_stream=io.StringIO(),
        )
        == 0
    )
    assert calls == [
        {
            "args": (None,),
            "kwargs": {"config_path": None, "require_existing_current": True},
        }
    ]


def test_restricted_activation_canary_skips_catalog_mutations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    snapshot = object()

    assert (
        preflight._ensure_preflight_catalog(
            object(),
            object(),
            snapshot,
            seed_starter_roster=_forbidden,
            ensure_no_match_fallback_roster=_forbidden,
            reconcile_packaged_contractors=_forbidden,
        )
        is snapshot
    )


@pytest.mark.parametrize("agent_type", ("default", "Code Reviewer"))
def test_exact_codex_subagent_start_staffs_the_real_child_uuid(
    monkeypatch: pytest.MonkeyPatch,
    agent_type: str,
) -> None:
    child_id = "11111111-1111-4111-8111-111111111111"
    observed: dict[str, Any] = {}

    class StartStore:
        def record_native_child_started(self, **kwargs: Any) -> dict[str, Any]:
            observed["started"] = kwargs
            return dict(kwargs)

    def staff(*_args: Any, **kwargs: Any) -> NativeChildStaffingResult:
        observed["staff"] = kwargs
        assert kwargs["delivery_validator"]("[AGENCY INFERENCE TEAM v6]") is True
        return NativeChildStaffingResult(
            staffed=True,
            reason_code="staffed",
            rewritten_task="[AGENCY INFERENCE TEAM v6]\nexact delivery",
            decision_id="decision-one",
            selected_ids=("code-reviewer",),
        )

    monkeypatch.setattr(
        hooks.HookBridge,
        "_restricted_codex_activation_child_parent_scope",
        lambda _self, _payload: ("session-one", "trace-one"),
    )
    monkeypatch.setattr(
        "agency_runtime.core.native_child_install_identity.current_runtime_managed_host_install_identity",
        lambda _host: object(),
    )
    monkeypatch.setattr(
        "agency_runtime.core.native_child_staffing.staff_native_child",
        staff,
    )
    monkeypatch.setattr(
        "agency_runtime.core.child_delivery_evidence._restricted_codex_canary_route",
        lambda *_args, **_kwargs: {
            "decision_id": "decision-one",
            "binding_id": child_id,
            "launch_id": child_id,
        },
    )

    response = hooks.HookBridge(  # type: ignore[arg-type]
        "codex",
        store=StartStore(),
        _master={"enabled": True},
    ).handle(
        {
            "hook_event_name": "SubagentStart",
            # Codex SubagentStart identifies the child session, not its parent.
            "session_id": child_id,
            "turn_id": child_id,
            "agent_id": child_id,
            "agent_type": agent_type,
        }
    )

    staff_call = observed["staff"]
    assert staff_call["task"] == CODEX_ACTIVATION_CANARY_WORK_UNIT
    assert staff_call["parent_session_id"] == "session-one"
    assert staff_call["parent_trace_id"] == "trace-one"
    assert staff_call["launch_id"] == child_id
    assert staff_call["binding_kind"] == "child_id"
    assert staff_call["binding_id"] == child_id
    assert observed["started"] == {
        "host": "codex",
        "backend": "spawn_agent",
        "session_id": "session-one",
        "trace_id": "trace-one",
        "work_unit_id": work_unit_id_from_text(CODEX_ACTIVATION_CANARY_WORK_UNIT),
        "worker_id": child_id,
        "native_run_id": f"codex-agent:{child_id}",
    }
    assert response == {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": "[AGENCY INFERENCE TEAM v6]\nexact delivery",
        }
    }


def _restricted_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.delenv("AGENCY_CODEX_ACTIVATION_QUERY_HASH", raising=False)


class _NoOpenTraceStore:
    def get_open_traces_for_session(self, _session_id: str) -> list[str]:
        return []


def test_restricted_child_join_derives_artifact_when_hint_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # AR-334: codex 0.151 ships no transcript path in the SubagentStart
    # payload; the sole child-named artifact under the canonical root is the
    # derivable fallback and the fail-closed parser stays the trust anchor.
    _restricted_env(monkeypatch)
    child_id = "01a04f93-7d59-75c1-a813-c3479e11cc16"
    parent_id = "01a04f92-e63c-76a2-9147-ee0636137875"
    root = tmp_path / "sessions"
    day = root / "2026" / "08" / "30"
    day.mkdir(parents=True)
    artifact = day / f"rollout-2026-08-30T00-00-00-{child_id}.jsonl"
    artifact.write_text("{}\n", encoding="utf-8")
    seen: dict[str, Any] = {}

    def fake_parser(path: Any, *, child_id: str, cwd: Any, root: Any = None) -> str:
        seen["path"] = str(path)
        seen["child"] = child_id
        return parent_id

    monkeypatch.setattr(
        "agency_runtime.core.child_delivery_evidence.default_child_artifact_root",
        lambda _host: root,
    )
    monkeypatch.setattr(
        "agency_runtime.core.child_delivery_evidence.codex_v1491_child_parent_session",
        fake_parser,
    )
    bridge = hooks.HookBridge(  # type: ignore[arg-type]
        "codex",
        store=_NoOpenTraceStore(),
        _master={"enabled": True},
    )

    scope = bridge._restricted_codex_activation_child_parent_scope(
        {
            "hook_event_name": "SubagentStart",
            "session_id": child_id,
            "agent_id": child_id,
            "cwd": str(tmp_path),
        }
    )

    assert scope is None
    assert seen["path"] == str(artifact)
    assert seen["child"] == child_id
    assert bridge._restricted_child_join_refusal == "parent_trace_ambiguous"


def test_restricted_child_join_accepts_both_session_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 0.150 SubagentStart carried the parent session; 0.151 carries the
    # child's own session. Both must reach the parent-trace stage, while a
    # third identity stays a mismatch.
    _restricted_env(monkeypatch)
    child_id = "01a04f93-7d59-75c1-a813-c3479e11cc16"
    parent_id = "01a04f92-e63c-76a2-9147-ee0636137875"
    other_id = "01a04f92-0000-7000-8000-000000000001"
    monkeypatch.setattr(
        "agency_runtime.core.child_delivery_evidence.codex_v1491_child_parent_session",
        lambda _path, *, child_id, cwd, root=None: parent_id,
    )
    bridge = hooks.HookBridge(  # type: ignore[arg-type]
        "codex",
        store=_NoOpenTraceStore(),
        _master={"enabled": True},
    )

    outcomes: dict[str, str] = {}
    for label, session_value in (
        ("parent-session", parent_id),
        ("child-session", child_id),
        ("third-party", other_id),
    ):
        scope = bridge._restricted_codex_activation_child_parent_scope(
            {
                "hook_event_name": "SubagentStart",
                "session_id": session_value,
                "agent_id": child_id,
                "cwd": str(tmp_path),
                "transcript_path": str(tmp_path / "rollout.jsonl"),
            }
        )
        assert scope is None
        outcomes[label] = bridge._restricted_child_join_refusal

    assert outcomes["parent-session"] == "parent_trace_ambiguous"
    assert outcomes["child-session"] == "parent_trace_ambiguous"
    assert outcomes["third-party"] == "parent_session_mismatch"


def test_unstaffed_codex_identity_names_the_join_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _restricted_env(monkeypatch)
    child_id = "11111111-1111-4111-8111-111111111111"

    class StartStore:
        def record_native_child_started(self, **kwargs: Any) -> dict[str, Any]:
            return dict(kwargs)

    def declining_scope(self: Any, _payload: Any) -> None:
        self._restricted_child_join_refusal = "parent_snapshot_contract_mismatch"
        return None

    monkeypatch.setattr(
        hooks.HookBridge,
        "_restricted_codex_activation_child_parent_scope",
        declining_scope,
    )
    response = hooks.HookBridge(  # type: ignore[arg-type]
        "codex",
        store=StartStore(),
        _master={"enabled": True},
    ).handle(
        {
            "hook_event_name": "SubagentStart",
            "session_id": child_id,
            "turn_id": child_id,
            "agent_id": child_id,
            "agent_type": "default",
        }
    )

    context = response["hookSpecificOutput"]["additionalContext"]
    assert 'restricted_join_refusal="parent_snapshot_contract_mismatch"' in context


def test_declined_join_writes_content_free_diagnostic_to_armed_sink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # AR-334: codex 0.151 swallows hook stderr and encrypts hook stdout, so
    # the armed diagnostics sink is the only host-observable record of which
    # branch declined the restricted join.
    _restricted_env(monkeypatch)
    sink = tmp_path / "agency-hook-join-diagnostics.jsonl"
    monkeypatch.setenv("AGENCY_CODEX_HOOK_EVENT_DIAGNOSTICS", "1")
    monkeypatch.setenv("AGENCY_CODEX_HOOK_DIAGNOSTICS_PATH", str(sink))

    class StartStore:
        def record_native_child_started(self, **kwargs: Any) -> dict[str, Any]:
            return dict(kwargs)

    bridge = hooks.HookBridge(  # type: ignore[arg-type]
        "codex",
        store=StartStore(),
        _master={"enabled": True},
    )
    bridge._handle_codex_subagent_start(
        {
            "hook_event_name": "SubagentStart",
            "session_id": "11111111-1111-4111-8111-111111111111",
            "turn_id": "11111111-1111-4111-8111-111111111111",
            "agent_type": "default",
            "cwd": str(tmp_path),
        }
    )

    lines = sink.read_text(encoding="ascii").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["event"] == "SubagentStart"
    assert entry["joined"] is False
    assert entry["refusal"] == "child_correlation_invalid"
    assert entry["agent_type_admitted"] is True
    assert entry["fields"] == [
        "agent_type",
        "cwd",
        "hook_event_name",
        "session_id",
        "turn_id",
    ]


def test_join_diagnostic_sink_stays_silent_without_diagnostics_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _restricted_env(monkeypatch)
    sink = tmp_path / "agency-hook-join-diagnostics.jsonl"
    monkeypatch.delenv("AGENCY_CODEX_HOOK_EVENT_DIAGNOSTICS", raising=False)
    monkeypatch.setenv("AGENCY_CODEX_HOOK_DIAGNOSTICS_PATH", str(sink))

    class StartStore:
        def record_native_child_started(self, **kwargs: Any) -> dict[str, Any]:
            return dict(kwargs)

    hooks.HookBridge(  # type: ignore[arg-type]
        "codex",
        store=StartStore(),
        _master={"enabled": True},
    )._handle_codex_subagent_start(
        {
            "hook_event_name": "SubagentStart",
            "session_id": "11111111-1111-4111-8111-111111111111",
            "turn_id": "11111111-1111-4111-8111-111111111111",
            "agent_type": "default",
            "agent_id": "11111111-1111-4111-8111-111111111111",
            "cwd": str(tmp_path),
        }
    )

    assert not sink.exists()


def test_sanitize_codex_hook_join_diagnostics_projects_only_exact_entries() -> None:
    from agency_runtime.core.codex_activation_verification import (
        sanitize_codex_hook_join_diagnostics,
    )

    valid = (
        '{"event": "SubagentStart", "fields": ["cwd", "session_id"],'
        ' "refusal": "parent_session_mismatch", "joined": false,'
        ' "agent_type_admitted": true}'
    )
    lines = "\n".join(
        [
            "not json",
            '{"event": "SubagentStart"}',
            '{"event": "Bad Event!", "fields": [], "refusal": "", "joined": true,'
            ' "agent_type_admitted": true}',
            '{"event": "SubagentStart", "fields": ["x"], "refusal": "Invalid-Slug",'
            ' "joined": true, "agent_type_admitted": true}',
            valid,
        ]
    )

    entries = sanitize_codex_hook_join_diagnostics(lines)

    assert entries == [
        {
            "event": "SubagentStart",
            "fields": ["cwd", "session_id"],
            "refusal": "parent_session_mismatch",
            "joined": False,
            "agent_type_admitted": True,
        }
    ]
    assert sanitize_codex_hook_join_diagnostics(None) == []


def test_restricted_join_artifact_parent_retries_late_rollout_flush(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The hook can outrun the host's rollout flush at SubagentStart; the
    # bounded re-read admits the file once it lands without weakening the
    # fail-closed parser.
    _restricted_env(monkeypatch)
    child_id = "01a04f93-7d59-75c1-a813-c3479e11cc16"
    parent_id = "01a04f92-e63c-76a2-9147-ee0636137875"
    artifact = tmp_path / f"rollout-2026-08-30T00-00-00-{child_id}.jsonl"
    attempts: list[int] = []
    sleeps: list[float] = []

    def late_artifact(self: Any, _child: str) -> str | None:
        attempts.append(1)
        return str(artifact) if len(attempts) >= 3 else None

    monkeypatch.setattr(hooks.HookBridge, "_sole_codex_child_artifact", late_artifact)
    monkeypatch.setattr(hooks.time, "sleep", lambda value: sleeps.append(value))
    monkeypatch.setattr(
        "agency_runtime.core.child_delivery_evidence.codex_v1491_child_parent_session",
        lambda _path, *, child_id, cwd, root=None: parent_id,
    )
    bridge = hooks.HookBridge(  # type: ignore[arg-type]
        "codex",
        store=_NoOpenTraceStore(),
        _master={"enabled": True},
    )

    parent = bridge._restricted_join_artifact_parent(
        {},
        hint_field="transcript_path",
        child_session_id=child_id,
        cwd=str(tmp_path),
    )

    assert parent == parent_id
    assert len(attempts) == 3
    assert sleeps == [0.2, 0.2]


def test_restricted_spawn_input_admits_hook_decrypted_canary_plaintext() -> None:
    # Codex 0.151 hands the PreToolUse hook the decrypted channel payload;
    # only the byte-exact fixed canary work unit is admitted in that form
    # (ADR-0194), beside the unchanged 0.150 opaque shape.
    base = {
        "agent_type": "Code Reviewer",
        "fork_turns": "none",
        "task_name": "code_reviewer",
    }
    admit = hooks.HookBridge._restricted_codex_spawn_input
    assert admit({**base, "message": CODEX_ACTIVATION_CANARY_WORK_UNIT}) is True
    assert admit({**base, "message": CODEX_ACTIVATION_CANARY_WORK_UNIT + " "}) is False
    assert admit({**base, "message": "review this repository please"}) is False
    assert admit({**base, "message": CODEX_ACTIVATION_CANARY_WORK_UNIT, "extra": "x"}) is False


def test_pre_tool_leaves_recognized_canary_spawn_to_restricted_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Inside the proven restricted parent scope, the recognized canary spawn
    # must not be consumed by ordinary plaintext staffing on any admitted
    # contract; the hook stays silent and non-blocking (ADR-0194).
    def scope(self: Any, _payload: Any) -> tuple[str, str]:
        return ("11111111-1111-7111-8111-111111111111", "trace-1")

    def forbidden(self: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("ordinary plaintext staffing must not run")

    monkeypatch.setattr(
        hooks.HookBridge,
        "_restricted_codex_activation_parent_scope",
        scope,
    )
    monkeypatch.setattr(hooks.HookBridge, "_staff_plaintext_native_child", forbidden)
    bridge = hooks.HookBridge(  # type: ignore[arg-type]
        "codex",
        store=object(),
        _master={"enabled": True},
    )

    response = bridge._handle_native_child_pre_tool_use(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "functions.collaboration.spawn_agent",
            "tool_input": {
                "agent_type": "Code Reviewer",
                "fork_turns": "none",
                "task_name": "code_reviewer",
                "message": CODEX_ACTIVATION_CANARY_WORK_UNIT,
            },
        }
    )

    assert response == {}


def test_codex_stop_join_staffs_the_canary_child_when_no_route_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Codex 0.151 exec never emits SubagentStart, so the stop join is the
    # first hook carrying the real child UUID; the child-bound canary
    # staffing decision is created there exactly once (ADR-0194).
    child_id = "01a04f93-7d59-75c1-a813-c3479e11cc16"
    parent_id = "01a04f92-e63c-76a2-9147-ee0636137875"
    staffed: list[str] = []

    def scope(self: Any, _payload: Any) -> tuple[str, str]:
        return (parent_id, "trace-1")

    def staff(self: Any, *, session_id: str, trace_id: str, identity: Any) -> str:
        staffed.append(identity.worker_id)
        return ""

    class StopStore:
        def record_native_child_stopped(self, **kwargs: Any) -> dict[str, Any]:
            return dict(kwargs)

    monkeypatch.setattr(
        hooks.HookBridge,
        "_restricted_codex_activation_child_parent_scope",
        scope,
    )
    monkeypatch.setattr(
        hooks.HookBridge,
        "_staff_restricted_codex_activation_child",
        staff,
    )
    routes: list[object] = [None, {"decision_id": "existing"}]
    monkeypatch.setattr(
        "agency_runtime.core.child_delivery_evidence._restricted_codex_canary_route",
        lambda *_args, **_kwargs: routes.pop(0),
    )
    monkeypatch.setattr(
        "agency_runtime.core.child_delivery_evidence."
        "_collect_restricted_codex_canary_child_delivery",
        lambda *_args, **_kwargs: None,
    )
    bridge = hooks.HookBridge(  # type: ignore[arg-type]
        "codex",
        store=StopStore(),
        _master={"enabled": True},
    )
    payload = {
        "hook_event_name": "SubagentStop",
        "session_id": child_id,
        "agent_id": child_id,
        "agent_type": "Code Reviewer",
        "cwd": "/tmp",
    }

    bridge._handle_codex_subagent_stop(payload)
    assert staffed == [child_id]

    bridge._handle_codex_subagent_stop(payload)
    assert staffed == [child_id]
