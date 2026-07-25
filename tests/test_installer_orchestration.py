"""Focused state-machine tests for installer orchestration helpers."""

from __future__ import annotations

import pytest

from agency_runtime.core import installer_orchestration as orchestration
from agency_runtime.core.installer_contracts import NativeCommandResult


@pytest.mark.parametrize(
    ("host", "enabled", "expected"),
    [
        ("hermes", True, ["hermes", "plugins", "enable", "agency-preflight"]),
        (
            "openclaw",
            False,
            ["openclaw", "plugins", "disable", "agency-preflight"],
        ),
        (
            "claude",
            True,
            [
                "claude",
                "plugin",
                "enable",
                "agency-preflight@agency-runtime",
                "--scope",
                "user",
            ],
        ),
        (
            "codex",
            False,
            [
                "codex",
                "plugin",
                "remove",
                "agency-preflight@agency-runtime",
                "--json",
            ],
        ),
    ],
)
def test_toggle_command_preserves_each_native_lifecycle(
    host: str,
    enabled: bool,
    expected: list[str],
) -> None:
    assert orchestration._toggle_command(host, enabled) == expected


@pytest.mark.parametrize(
    ("steps", "failed_step", "expected"),
    [
        (
            [{"name": "inspect_existing", "ok": True}],
            "install",
            (
                "partial_failure",
                "staged-registration-incomplete",
                True,
                None,
                None,
            ),
        ),
        (
            [{"name": "inspect_existing", "ok": False}],
            "install",
            (
                "partial_failure",
                "staged-registration-incomplete",
                None,
                None,
                None,
            ),
        ),
        (
            [{"name": "runtime_inspect", "loaded": False}],
            "runtime_inspect_unproven",
            (
                "verification_incomplete",
                "enabled-runtime-unverified",
                True,
                True,
                False,
            ),
        ),
        (
            [],
            "gateway_status_unproven",
            (
                "partial_failure",
                "staged-registration-incomplete",
                None,
                None,
                None,
            ),
        ),
    ],
)
def test_openclaw_failure_facts_preserve_proven_maturity_only(
    steps: list[dict[str, object]],
    failed_step: str,
    expected: tuple[str, str, bool | None, bool | None, bool | None],
) -> None:
    assert orchestration._openclaw_failure_facts(steps, failed_step) == expected


def _native_result(returncode: int, *, stdout: str = "", stderr: str = "") -> NativeCommandResult:
    return NativeCommandResult(
        command=("host", "command"),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


@pytest.mark.parametrize(
    ("native", "verification", "enabled", "expected"),
    [
        (
            _native_result(4, stderr="toggle failed"),
            orchestration._ToggleVerification(),
            True,
            "command_failed",
        ),
        (
            _native_result(0),
            orchestration._ToggleVerification(inventory=_native_result(5)),
            True,
            "inventory_failed",
        ),
        (
            _native_result(0),
            orchestration._ToggleVerification(
                inventory=_native_result(0),
                record={"enabled": True},
                native_flag=True,
                postcondition=True,
                observed_enabled=True,
            ),
            True,
            "verified",
        ),
        (
            _native_result(0),
            orchestration._ToggleVerification(
                inventory=_native_result(0),
                record={"pluginId": "agency-preflight"},
            ),
            True,
            "enablement_unverified",
        ),
        (
            _native_result(0),
            orchestration._ToggleVerification(
                inventory=_native_result(0),
                record={"enabled": True},
                native_flag=True,
            ),
            False,
            "postcondition_mismatch",
        ),
    ],
)
def test_toggle_verification_state_distinguishes_failure_boundaries(
    native: NativeCommandResult,
    verification: orchestration._ToggleVerification,
    enabled: bool,
    expected: str,
) -> None:
    assert (
        orchestration._toggle_verification_state(
            native,
            verification,
            enabled=enabled,
        )
        == expected
    )


def test_unknown_host_results_keep_public_schema_distinctions() -> None:
    install = orchestration.install_agent_adapter("unknown")
    rollback = orchestration.rollback_agent_adapter("unknown")
    toggle = orchestration.toggle_agency("unknown", True)

    assert install == {
        "ok": False,
        "exit_code": 2,
        "error": "Unknown host: unknown. Supported: hermes, openclaw, codex, claude, zcode",
    }
    assert (
        rollback
        == toggle
        == {
            "ok": False,
            "exit_code": 2,
            "error": "Unknown host: unknown",
        }
    )
