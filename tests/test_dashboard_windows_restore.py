from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

import agency_runtime.core.dashboard_service_windows as windows
from agency_runtime.core.dashboard_service_core import _CommandResult, _Context


def _context() -> _Context:
    root = Path("C:/agency-runtime-dashboard-restore-test")
    return _Context(
        platform="windows",
        home=root,
        config_path=root / "agency.yaml",
        python_executable=root / "python.exe",
        manager="windows-task-scheduler",
        registration="Agency Runtime Dashboard",
        unit_path=None,
        manifest_path=root / "dashboard-service.json",
        worker_argv=(str(root / "python.exe"), "-m", "agency_runtime.cli"),
        windows_user="S-1-5-21-test",
    )


def _result(name: str, *, ok: bool = True, stdout: str = "") -> _CommandResult:
    return _CommandResult(
        command=(name,),
        returncode=0 if ok else 1,
        stdout=stdout,
        stderr="injected failure" if not ok else "",
    )


def _sequence(values: list[object]) -> Callable[[], object]:
    iterator: Iterator[object] = iter(values)

    def next_value() -> object:
        try:
            return next(iterator)
        except StopIteration as exc:  # pragma: no cover - assertion guard
            raise AssertionError("unexpected extra rollback probe") from exc

    return next_value


def _patch_registration_queries(
    monkeypatch: pytest.MonkeyPatch,
    values: list[tuple[str, _CommandResult]],
) -> None:
    next_value = _sequence(list(values))
    monkeypatch.setattr(
        windows,
        "_query_windows_registration",
        lambda **_kwargs: next_value(),
    )


def _patch_owned_registration(
    monkeypatch: pytest.MonkeyPatch,
    *,
    property_values: dict[str, str],
) -> None:
    monkeypatch.setattr(windows, "_windows_xml_owned", lambda _content: True)
    monkeypatch.setattr(windows, "_manifest_owned", lambda _ctx: True)
    monkeypatch.setattr(
        windows,
        "_windows_task_properties",
        lambda content: property_values.get(content, content),
    )
    monkeypatch.setattr(windows, "_restore_file", lambda _path, _prior: None)
    monkeypatch.setattr(windows, "_file_matches", lambda _path, _prior: True)
    monkeypatch.setattr(
        windows,
        "_register_windows_xml",
        lambda *_args, **_kwargs: _result("create"),
    )


def test_restore_reports_registration_verification_failure_in_command_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_owned_registration(
        monkeypatch,
        property_values={"prior": "prior", "current": "current", "bad": "bad"},
    )
    _patch_registration_queries(
        monkeypatch,
        [
            ("present", _result("current", stdout="current")),
            ("present", _result("recheck", stdout="current")),
            ("present", _result("verify-restored", stdout="bad")),
            ("present", _result("verify-final", stdout="prior")),
        ],
    )
    monkeypatch.setattr(
        windows,
        "_windows_running_state",
        lambda **_kwargs: (False, _result("active-final")),
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task="prior",
        prior_manifest=b"manifest",
        prior_active=False,
        command_runner=None,
    )

    assert outcome.succeeded is False
    assert outcome.error == "Windows rollback registration verification failed"
    assert [item["command"][0] for item in outcome.commands] == [
        "current",
        "recheck",
        "create",
        "verify-restored",
        "verify-final",
        "active-final",
    ]


def test_restore_reports_indeterminate_active_state_but_still_verifies_final_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_owned_registration(
        monkeypatch,
        property_values={"prior": "prior", "current": "current"},
    )
    _patch_registration_queries(
        monkeypatch,
        [
            ("present", _result("current", stdout="current")),
            ("present", _result("recheck", stdout="current")),
            ("present", _result("verify-restored", stdout="prior")),
            ("present", _result("verify-final", stdout="prior")),
        ],
    )
    next_active = _sequence(
        [(None, _result("active-indeterminate")), (False, _result("active-final"))]
    )
    monkeypatch.setattr(
        windows,
        "_windows_running_state",
        lambda **_kwargs: next_active(),
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task="prior",
        prior_manifest=b"manifest",
        prior_active=False,
        command_runner=None,
    )

    assert outcome.succeeded is False
    assert outcome.error == "Windows rollback active-state verification is indeterminate"
    assert outcome.commands[-2]["command"] == ["verify-final"]
    assert outcome.commands[-1]["command"] == ["active-final"]


def test_restore_reports_failed_active_state_mutation_and_runs_final_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_owned_registration(
        monkeypatch,
        property_values={"prior": "prior", "current": "current"},
    )
    _patch_registration_queries(
        monkeypatch,
        [
            ("present", _result("current", stdout="current")),
            ("present", _result("recheck", stdout="current")),
            ("present", _result("verify-restored", stdout="prior")),
            ("present", _result("verify-final", stdout="prior")),
        ],
    )
    next_active = _sequence([(False, _result("active-before")), (False, _result("active-final"))])
    monkeypatch.setattr(
        windows,
        "_windows_running_state",
        lambda **_kwargs: next_active(),
    )
    monkeypatch.setattr(
        windows,
        "_assert_windows_task_unchanged",
        lambda *_args, **_kwargs: _result("exact-recheck"),
    )
    monkeypatch.setattr(
        windows,
        "_run",
        lambda *_args, **_kwargs: _result("run", ok=False),
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task="prior",
        prior_manifest=b"manifest",
        prior_active=True,
        command_runner=None,
    )

    assert outcome.succeeded is False
    assert outcome.error == "Windows rollback active-state restoration failed"
    assert [item["command"][0] for item in outcome.commands[-4:]] == [
        "exact-recheck",
        "run",
        "verify-final",
        "active-final",
    ]


def test_created_task_recheck_conflict_invalidates_manifest_without_deleting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    restored_files: list[tuple[Path, bytes | None]] = []
    monkeypatch.setattr(windows, "_windows_xml_owned", lambda _content: True)
    monkeypatch.setattr(windows, "_windows_definition_matches", lambda *_args: True)
    monkeypatch.setattr(windows, "_manifest_owned", lambda _ctx: True)
    monkeypatch.setattr(
        windows,
        "_restore_file",
        lambda path, prior: restored_files.append((path, prior)),
    )
    monkeypatch.setattr(windows, "_file_matches", lambda _path, _prior: False)
    _patch_registration_queries(
        monkeypatch,
        [
            ("present", _result("current", stdout="owned-current")),
            ("present", _result("recheck", stdout="owned-replacement")),
            ("present", _result("verify-final", stdout="owned-replacement")),
        ],
    )
    monkeypatch.setattr(
        windows,
        "_run",
        lambda *_args, **_kwargs: pytest.fail("conflicting task must not be deleted"),
    )
    ctx = _context()

    outcome = windows._restore_windows_state(
        ctx,
        prior_task=None,
        prior_manifest=None,
        prior_active=False,
        created_registration=True,
        command_runner=None,
    )

    assert outcome.succeeded is False
    assert outcome.error == (
        "unsafe Windows rollback refused: created task changed; ownership manifest removed"
    )
    assert restored_files == [(ctx.manifest_path, None)]
    assert [item["command"][0] for item in outcome.commands] == [
        "current",
        "recheck",
        "verify-final",
    ]


@pytest.mark.parametrize("delete_ok", [True, False])
def test_created_task_delete_result_is_verified(
    monkeypatch: pytest.MonkeyPatch,
    delete_ok: bool,
) -> None:
    _patch_owned_registration(monkeypatch, property_values={})
    monkeypatch.setattr(windows, "_windows_definition_matches", lambda *_args: True)
    _patch_registration_queries(
        monkeypatch,
        [
            ("present", _result("current", stdout="owned")),
            ("present", _result("recheck", stdout="owned")),
            (
                "absent" if delete_ok else "present",
                _result("verify-final", stdout="" if delete_ok else "owned"),
            ),
        ],
    )
    monkeypatch.setattr(
        windows,
        "_run",
        lambda *_args, **_kwargs: _result("delete", ok=delete_ok),
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task=None,
        prior_manifest=None,
        prior_active=False,
        created_registration=True,
        command_runner=None,
    )

    assert outcome.succeeded is delete_ok
    assert outcome.error == (None if delete_ok else "scheduled-task rollback deletion failed")
    assert [item["command"][0] for item in outcome.commands] == [
        "current",
        "recheck",
        "delete",
        "verify-final",
    ]


def test_uncreated_absent_task_is_left_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_owned_registration(monkeypatch, property_values={})
    _patch_registration_queries(
        monkeypatch,
        [
            ("absent", _result("current")),
            ("absent", _result("verify-final")),
        ],
    )
    monkeypatch.setattr(
        windows,
        "_run",
        lambda *_args, **_kwargs: pytest.fail("no task was created by this transaction"),
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task=None,
        prior_manifest=None,
        prior_active=False,
        command_runner=None,
    )

    assert outcome.succeeded is True
    assert outcome.error is None


def test_created_task_ownership_mismatch_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_owned_registration(monkeypatch, property_values={})
    monkeypatch.setattr(windows, "_manifest_owned", lambda _ctx: False)
    _patch_registration_queries(
        monkeypatch,
        [
            ("absent", _result("current")),
            ("absent", _result("verify-final")),
        ],
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task=None,
        prior_manifest=None,
        prior_active=False,
        created_registration=True,
        command_runner=None,
    )

    assert outcome.succeeded is False
    assert outcome.error == ("unsafe Windows rollback refused: created task ownership changed")


@pytest.mark.parametrize("stable_absence", [True, False])
def test_prior_task_absence_is_rechecked_before_recreation(
    monkeypatch: pytest.MonkeyPatch,
    stable_absence: bool,
) -> None:
    _patch_owned_registration(monkeypatch, property_values={"prior": "prior"})
    queries = [
        ("absent", _result("current")),
        (
            "absent" if stable_absence else "present",
            _result("recheck", stdout="" if stable_absence else "replacement"),
        ),
    ]
    if stable_absence:
        queries.append(("present", _result("verify-restored", stdout="prior")))
    queries.append(("present", _result("verify-final", stdout="prior")))
    _patch_registration_queries(monkeypatch, queries)
    forces: list[bool] = []

    def register(*_args: object, force: bool, **_kwargs: object) -> _CommandResult:
        forces.append(force)
        return _result("create")

    monkeypatch.setattr(windows, "_register_windows_xml", register)
    monkeypatch.setattr(
        windows,
        "_windows_running_state",
        lambda **_kwargs: (False, _result("active")),
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task="prior",
        prior_manifest=b"manifest",
        prior_active=False,
        command_runner=None,
    )

    assert outcome.succeeded is stable_absence
    assert forces == ([False] if stable_absence else [])
    assert outcome.error == (
        None
        if stable_absence
        else "unsafe Windows rollback refused: task absence changed; ownership manifest removed"
    )


def test_indeterminate_task_state_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_owned_registration(monkeypatch, property_values={"prior": "prior"})
    monkeypatch.setattr(windows, "_manifest_owned", lambda _ctx: False)
    _patch_registration_queries(
        monkeypatch,
        [
            ("indeterminate", _result("current", ok=False)),
            ("present", _result("verify-final", stdout="prior")),
        ],
    )
    monkeypatch.setattr(
        windows,
        "_windows_running_state",
        lambda **_kwargs: (False, _result("active-final")),
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task="prior",
        prior_manifest=b"manifest",
        prior_active=False,
        command_runner=None,
    )

    assert outcome.succeeded is False
    assert outcome.error == ("unsafe Windows rollback refused: task state is indeterminate")


def test_unowned_existing_task_is_never_replaced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_owned_registration(monkeypatch, property_values={"prior": "prior"})
    monkeypatch.setattr(windows, "_manifest_owned", lambda _ctx: False)
    _patch_registration_queries(
        monkeypatch,
        [
            ("present", _result("current", stdout="unowned")),
            ("present", _result("verify-final", stdout="prior")),
        ],
    )
    monkeypatch.setattr(
        windows,
        "_windows_running_state",
        lambda **_kwargs: (False, _result("active-final")),
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task="prior",
        prior_manifest=b"manifest",
        prior_active=False,
        command_runner=None,
    )

    assert outcome.succeeded is False
    assert outcome.error == ("unsafe Windows rollback refused: task ownership changed")
    assert [item["command"][0] for item in outcome.commands] == [
        "current",
        "verify-final",
        "active-final",
    ]


def test_registration_mutation_failure_is_not_masked_by_final_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_owned_registration(
        monkeypatch,
        property_values={"prior": "prior", "current": "current"},
    )
    _patch_registration_queries(
        monkeypatch,
        [
            ("present", _result("current", stdout="current")),
            ("present", _result("recheck", stdout="current")),
            ("present", _result("verify-final", stdout="prior")),
        ],
    )
    monkeypatch.setattr(
        windows,
        "_register_windows_xml",
        lambda *_args, **_kwargs: _result("create", ok=False),
    )
    monkeypatch.setattr(
        windows,
        "_windows_running_state",
        lambda **_kwargs: (False, _result("active-final")),
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task="prior",
        prior_manifest=b"manifest",
        prior_active=False,
        command_runner=None,
    )

    assert outcome.succeeded is False
    assert outcome.error == "scheduled-task rollback registration failed"


def test_manifest_restore_error_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_owned_registration(
        monkeypatch,
        property_values={"prior": "prior", "current": "current"},
    )
    _patch_registration_queries(
        monkeypatch,
        [
            ("present", _result("current", stdout="current")),
            ("present", _result("recheck", stdout="current")),
            ("present", _result("verify-final", stdout="prior")),
        ],
    )
    monkeypatch.setattr(
        windows,
        "_restore_file",
        lambda *_args: (_ for _ in ()).throw(OSError("manifest restore failed")),
    )
    monkeypatch.setattr(
        windows,
        "_windows_running_state",
        lambda **_kwargs: (False, _result("active-final")),
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task="prior",
        prior_manifest=b"manifest",
        prior_active=False,
        command_runner=None,
    )

    assert outcome.succeeded is False
    assert outcome.error == "manifest restore failed"


@pytest.mark.parametrize("prior_active", [True, False])
def test_active_state_is_reconciled_in_both_directions(
    monkeypatch: pytest.MonkeyPatch,
    prior_active: bool,
) -> None:
    _patch_owned_registration(
        monkeypatch,
        property_values={"prior": "prior", "current": "current"},
    )
    _patch_registration_queries(
        monkeypatch,
        [
            ("present", _result("current", stdout="current")),
            ("present", _result("recheck", stdout="current")),
            ("present", _result("verify-restored", stdout="prior")),
            ("present", _result("verify-final", stdout="prior")),
        ],
    )
    next_active = _sequence(
        [
            (not prior_active, _result("active-before")),
            (prior_active, _result("active-final")),
        ]
    )
    monkeypatch.setattr(
        windows,
        "_windows_running_state",
        lambda **_kwargs: next_active(),
    )
    monkeypatch.setattr(
        windows,
        "_assert_windows_task_unchanged",
        lambda *_args, **_kwargs: _result("exact-recheck"),
    )
    operations: list[str] = []

    def mutate(argv: list[str], **_kwargs: object) -> _CommandResult:
        operations.append(argv[1])
        return _result("active-mutation")

    monkeypatch.setattr(windows, "_run", mutate)

    outcome = windows._restore_windows_state(
        _context(),
        prior_task="prior",
        prior_manifest=b"manifest",
        prior_active=prior_active,
        command_runner=None,
    )

    assert outcome.succeeded is True
    assert operations == ["/Run" if prior_active else "/End"]


def test_unexpected_restore_exception_is_reported_before_final_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_owned_registration(monkeypatch, property_values={})
    _patch_registration_queries(
        monkeypatch,
        [("absent", _result("verify-final"))],
    )
    monkeypatch.setattr(
        windows,
        "_restore_windows_registration",
        lambda _transaction: (_ for _ in ()).throw(UnicodeError("invalid XML")),
    )

    outcome = windows._restore_windows_state(
        _context(),
        prior_task=None,
        prior_manifest=None,
        prior_active=False,
        command_runner=None,
    )

    assert outcome.succeeded is False
    assert outcome.error == "invalid XML"
    assert [item["command"][0] for item in outcome.commands] == ["verify-final"]
