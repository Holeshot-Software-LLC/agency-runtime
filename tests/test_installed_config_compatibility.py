"""A config write must not brick the hooks that have to read it.

`agency config set` rewrites the whole document through the current renderer,
so a CLI newer than the last install stamps fields the installed projection has
never heard of onto sections nobody touched. Both validators are strict
allowlists, so the projection then raises "contains unsupported fields" -- and
hooks parse config on every event, so the box stops working entirely.

Observed 2026-08-11 on a live machine: setting an unrelated selector flag added
`token_parameter` to both providers, and every turn afterwards failed its
evidence contract with a message naming neither the field nor the file.

The guard has two duties and they pull against each other: refuse a document
the installed hooks demonstrably reject, and never block an edit on a machine
where no verdict can be obtained. Both are pinned here.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agency_runtime.core import installed_config_compatibility as guard


class _Completed:
    def __init__(self, returncode: int, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr


def test_an_unrelated_setting_does_not_rewrite_the_providers() -> None:
    """The cause behind the guard: validation normalizes, and the write persisted it.

    Setting a `selector` flag stamped `token_parameter` onto both providers,
    because validation returns every default materialized rather than merely
    checking. The narrow write carries only the paths an operation touched.
    """

    from agency_runtime.core.configuration_patch import narrowed_document

    pristine = {
        "providers": [{"name": "codex-subscription", "type": "cli", "model": "gpt-5.6-terra"}],
        "profile": "yolo",
    }
    normalized_and_patched = {
        "providers": [
            {
                "name": "codex-subscription",
                "type": "cli",
                "model": "gpt-5.6-terra",
                "token_parameter": "",
                "reasoning_effort": "",
            }
        ],
        "profile": "yolo",
        "selector": {"record_routing_intent": True},
    }

    persisted = narrowed_document(
        pristine, normalized_and_patched, {"selector.record_routing_intent"}
    )

    assert persisted is not None
    assert persisted["selector"] == {"record_routing_intent": True}
    # The whole point: providers are byte-for-byte what the operator had.
    assert persisted["providers"] == pristine["providers"]
    assert "token_parameter" not in str(persisted)


def test_narrowing_refuses_rather_than_dropping_a_change_it_cannot_place() -> None:
    """A provider secret addresses a list element, which a mapping walk cannot reach.

    Returning a partial document there would silently discard the edit, so the
    caller is told to persist the fully normalized document instead.
    """

    from agency_runtime.core.configuration_patch import narrowed_document

    assert (
        narrowed_document(
            {"providers": [{"name": "p"}]},
            {"providers": [{"name": "p", "api_key": "secret"}]},
            {"providers.0.api_key"},
        )
        is None
    )


def test_an_edit_that_really_is_about_providers_still_writes_them() -> None:
    from agency_runtime.core.configuration_patch import narrowed_document

    persisted = narrowed_document(
        {"providers": [{"name": "old"}], "profile": "yolo"},
        {"providers": [{"name": "new"}], "profile": "yolo"},
        {"providers"},
    )

    assert persisted is not None
    assert persisted["providers"] == [{"name": "new"}]


def test_no_installed_projection_is_not_a_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A machine that never installed must still be able to edit its config."""

    monkeypatch.setattr(guard, "_installed_projections", lambda: [])

    assert guard.installed_projection_rejection(tmp_path / "agency.yaml") == ""


def test_a_definite_rejection_is_reported_with_its_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        guard, "_installed_projections", lambda: [("bb45af11309a" + "0" * 52, tmp_path)]
    )
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: _Completed(
            1,
            "agency_runtime.core.configuration_contracts.ConfigValidationError: "
            "providers.0: contains unsupported fields\n",
        ),
    )

    message = guard.installed_projection_rejection(tmp_path / "agency.yaml")

    assert "providers.0: contains unsupported fields" in message
    assert "bb45af11309a" in message
    # The remedy has to be in the message: the operator sees this instead of a
    # broken box, and "which install" is the only actionable part.
    assert "agency install" in message


def test_an_accepted_document_is_not_a_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(guard, "_installed_projections", lambda: [("a" * 64, tmp_path)])
    monkeypatch.setattr(guard.subprocess, "run", lambda *a, **k: _Completed(0))

    assert guard.installed_projection_rejection(tmp_path / "agency.yaml") == ""


@pytest.mark.parametrize(
    "boom",
    [OSError("no interpreter"), subprocess.TimeoutExpired(cmd="probe", timeout=1.0)],
)
def test_an_unrunnable_probe_never_blocks_the_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boom: Exception
) -> None:
    """Failing closed here would make a broken probe lock an operator out."""

    def _raise(*args: object, **kwargs: object) -> None:
        raise boom

    monkeypatch.setattr(guard, "_installed_projections", lambda: [("a" * 64, tmp_path)])
    monkeypatch.setattr(guard.subprocess, "run", _raise)

    assert guard.installed_projection_rejection(tmp_path / "agency.yaml") == ""


def test_a_probe_that_broke_for_its_own_reasons_is_not_a_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing dependency inside the projection says nothing about the document."""

    monkeypatch.setattr(guard, "_installed_projections", lambda: [("a" * 64, tmp_path)])
    monkeypatch.setattr(
        guard.subprocess,
        "run",
        lambda *a, **k: _Completed(1, "ModuleNotFoundError: No module named 'yaml'\n"),
    )

    assert guard.installed_projection_rejection(tmp_path / "agency.yaml") == ""


def test_a_projection_matching_this_source_is_not_probed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hooks running this very code cannot disagree with it."""

    monkeypatch.setattr(guard, "running_runtime_digest", lambda: "d" * 64)
    monkeypatch.setattr(guard, "_recorded_hosts", lambda: ("claude",))
    monkeypatch.setattr(guard, "installed_runtime_pointer", lambda host: ("d" * 64, host))

    assert guard._installed_projections() == []


def test_the_config_preflight_refuses_a_rejected_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard has to be wired into the write path, not merely importable."""

    from agency_runtime.core import configuration
    from agency_runtime.core.configuration_contracts import ConfigValidationError

    monkeypatch.setattr(configuration, "_environment_overrides", lambda: {})
    monkeypatch.setattr(configuration, "_effective_document", lambda path: {})
    # The guard only inspects the file the hooks will actually read, so the
    # candidate has to sit beside the resolved live config for it to engage.
    monkeypatch.setattr(configuration, "resolve_config_path", lambda _=None: tmp_path / "live.yaml")
    monkeypatch.setattr(
        guard, "installed_projection_rejection", lambda path: "installed hooks cannot read this"
    )

    with pytest.raises(ConfigValidationError, match="installed hooks cannot read this"):
        configuration._preflight_effective_candidate(tmp_path / "agency.yaml")


def test_a_candidate_outside_the_live_config_directory_is_not_probed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Otherwise every test that writes a config depends on this machine's install.

    Checking a temp-file candidate against the real installed projection made
    four unrelated configuration tests fail on a box whose install was behind
    the source -- a machine-sensitive failure invented by the guard itself.
    """

    from agency_runtime.core import configuration

    monkeypatch.setattr(configuration, "_environment_overrides", lambda: {})
    monkeypatch.setattr(configuration, "_effective_document", lambda path: {})
    monkeypatch.setattr(
        configuration, "resolve_config_path", lambda _=None: tmp_path / "elsewhere" / "live.yaml"
    )

    def _explode(path: Path) -> str:
        raise AssertionError("the guard must not run for a candidate hooks never read")

    monkeypatch.setattr(guard, "installed_projection_rejection", _explode)

    configuration._preflight_effective_candidate(tmp_path / "agency.yaml")
