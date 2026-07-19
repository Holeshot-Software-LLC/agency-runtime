from __future__ import annotations

import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import (
    configuration_patch as patching,
)
from agency_runtime.core import (
    configuration_persistence as persistence,
)
from agency_runtime.core import (
    configuration_schema as schema,
)
from agency_runtime.core import (
    configuration_service as service,
)
from agency_runtime.core.bounded_io import FileSizeLimitError, UnsafeFileError
from agency_runtime.core.configuration_contracts import (
    MAX_CONFIG_BYTES,
    ConfigConflictError,
    ConfigLockError,
    ConfigurationError,
    ConfigValidationError,
)
from agency_runtime.core.windows_acl import WindowsTokenProbeError


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (schema._mapping, ([], "section")),
        (schema._string, (1, "field")),
        (schema._string, ("bad\0text", "field")),
        (
            lambda value, path: schema._number(value, path, minimum=0.0, maximum=2.0),
            ("1", "field"),
        ),
        (schema._choice, ("missing", "field", frozenset({"valid"}))),
        (schema._url, ("http://localhost:bad", "url")),
        (schema._loopback_host, ("example.test", "host")),
        (schema._string_list, (("not", "a", "list"), "items")),
        (schema._string_list, (["item"] * 129, "items")),
    ],
)
def test_schema_scalar_validators_reject_hostile_shapes(
    function: Any, args: tuple[Any, ...]
) -> None:
    with pytest.raises(ConfigValidationError):
        function(*args)


def test_schema_loopback_classifier_covers_rejection_and_localhost() -> None:
    assert schema._is_loopback_url("ftp://127.0.0.1") is False
    assert schema._is_loopback_url("http://user@127.0.0.1") is False
    assert schema._is_loopback_url("http://localhost") is True
    assert schema._is_loopback_url("http://[invalid") is False


@pytest.mark.parametrize(
    "provider",
    [
        {"unsupported": True},
        {
            "name": "cli",
            "type": "cli",
            "transport": "codex",
            "model": "",
            "base_url": "http://127.0.0.1",
        },
        {
            "name": "remote",
            "type": "anthropic",
            "model": "model",
            "base_url": "https://example.test",
            "api_key_env": "KEY",
            "transport": "codex",
        },
    ],
)
def test_schema_provider_rejects_unsupported_or_conflicting_fields(
    provider: dict[str, Any],
) -> None:
    with pytest.raises(ConfigValidationError):
        schema._validate_provider(provider, 0)


@pytest.mark.parametrize(
    ("validator", "value"),
    [
        (schema._validate_providers, {}),
        (schema._validate_judge, {"unsupported": True}),
        (schema._validate_ollama, {"unsupported": True}),
        (schema._validate_selector, {"unsupported": True}),
        (schema._validate_delegation, {"unsupported": True}),
        (schema._validate_agents, {"unsupported": True}),
        (schema._validate_store, {"unsupported": True}),
        (schema._validate_server, {"unsupported": True}),
        (schema._validate_dashboard, {"unsupported": True}),
        (schema._validate_observability, {"unsupported": True}),
        (lambda value: schema._validate_adapter_entry(value, "hermes"), {"api_key": "x"}),
        (schema._validate_adapters, {"unsupported": {}}),
        (schema.validate_config_document, []),
    ],
)
def test_schema_sections_reject_unknown_fields_and_roots(validator: Any, value: Any) -> None:
    with pytest.raises(ConfigValidationError):
        validator(value)


def test_schema_delegation_thresholds_must_be_monotonic() -> None:
    with pytest.raises(
        ConfigValidationError,
        match="must be greater than or equal to preferred_min_units",
    ):
        schema._validate_delegation(
            {
                "preferred_min_units": 4,
                "strongly_preferred_min_units": 3,
            }
        )


def test_schema_agents_rejects_protected_coordinator_disablement() -> None:
    with pytest.raises(ConfigValidationError, match="protected coordinator"):
        schema._validate_agents({"disabled": ["chief-of-staff"]})


def test_patch_provider_and_nested_shape_guards() -> None:
    with pytest.raises(ConfigValidationError, match="must be a list"):
        patching._providers_for_operation({})
    with pytest.raises(ConfigValidationError, match="must be a mapping"):
        patching._providers_for_operation(["invalid"])
    with pytest.raises(ConfigValidationError, match="existing configuration shape"):
        patching._nested_set({"judge": "invalid"}, "judge.model", "model")


@pytest.mark.parametrize(
    ("document", "path", "message"),
    [
        ({"judge": []}, "judge.api_key", "existing configuration shape"),
        ({"adapters": []}, "adapters.litellm.api_key", "existing configuration shape"),
        (
            {"adapters": {"litellm": []}},
            "adapters.litellm.api_key",
            "existing configuration shape",
        ),
        ({"providers": []}, "providers.bad.api_key", "path is not supported"),
        ({"providers": []}, "providers.0.api_key", "target does not exist"),
        ({"providers": ["invalid"]}, "providers.0.api_key", "target is invalid"),
    ],
)
def test_patch_secret_targets_fail_closed_on_ambiguous_shapes(
    document: dict[str, Any], path: str, message: str
) -> None:
    with pytest.raises(ConfigValidationError, match=message):
        patching._secret_target(document, path)


def test_patch_secret_target_builds_litellm_section() -> None:
    target, key = patching._secret_target({}, "adapters.litellm.api_key")
    assert target == {}
    assert key == "api_key"


def test_provider_list_preserves_multiple_existing_secrets() -> None:
    document = {
        "providers": [
            {"name": "first", "api_key": "one"},
            {"name": "second", "api_key": "two"},
        ]
    }
    patching._apply_provider_list(
        document,
        [{"name": "first"}, {"name": "second"}],
    )
    assert [provider["api_key"] for provider in document["providers"]] == [
        "one",
        "two",
    ]
    document = {"providers": [{}, {"name": "second", "api_key": "two"}]}
    patching._apply_provider_list(document, [{"name": "second"}])
    assert document["providers"][0]["api_key"] == "two"


@pytest.mark.parametrize(
    "operation",
    [
        {"op": "secret", "path": 1, "action": "clear"},
        {"op": "secret", "path": "judge.api_key", "action": "invalid"},
        {
            "op": "secret",
            "path": "judge.api_key",
            "action": "clear",
            "extra": True,
        },
    ],
)
def test_patch_secret_operation_validates_contract(operation: dict[str, Any]) -> None:
    with pytest.raises(ConfigValidationError):
        patching._apply_secret_operation({}, operation)


def test_local_only_policy_repairs_malformed_sections_and_remote_providers() -> None:
    document: dict[str, Any] = {
        "profile": "local-only",
        "ollama": [],
        "judge": [],
        "providers": [None, {"name": "remote", "type": "anthropic", "base_url": "https://x"}],
        "adapters": [],
    }
    assert patching._enforce_local_only(document) is True
    assert document["providers"][0]["type"] == "ollama"
    assert isinstance(document["adapters"], dict)

    entries: dict[str, Any] = {
        "profile": "local-only",
        "adapters": {name: [] for name in ("litellm", "hermes", "openclaw", "codex", "claude")},
    }
    assert patching._enforce_local_only(entries) is True
    assert all(entry == {"enabled": "false"} for entry in entries["adapters"].values())


def test_patch_batch_and_operation_contract_errors() -> None:
    assert patching._diff_paths(1, 2) == {"configuration"}
    for operations in ("invalid", []):
        with pytest.raises(ConfigValidationError):
            patching.validate_operation_batch(operations)  # type: ignore[arg-type]
    for operation in (
        "invalid",
        {"op": "set", "path": "profile", "value": "standard", "extra": True},
        {"op": "set", "path": 1, "value": "standard"},
        {"op": "unsupported"},
    ):
        with pytest.raises(ConfigValidationError):
            patching.apply_operations({}, [operation])  # type: ignore[list-item]


def test_persistence_read_and_parse_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(persistence, "assert_config_namespace", lambda _path: None)
    monkeypatch.setattr(persistence, "_ensure_config_file_private", lambda _path: True)
    monkeypatch.setattr(
        persistence,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileSizeLimitError("large")),
    )
    with pytest.raises(ConfigValidationError, match="size limit"):
        persistence.read_raw(Path("config"))
    monkeypatch.setattr(
        persistence,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
    )
    with pytest.raises(ConfigurationError, match="could not be read"):
        persistence.read_raw(Path("config"))
    with pytest.raises(ConfigValidationError, match="root must be a mapping"):
        persistence.parse_document(b"[]")


def test_permission_restriction_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ConfigurationError, match="symlink"):
        persistence.restrict_permissions(Path("config"), path_check=lambda _path: True)

    with pytest.raises(ConfigurationError, match="probe"):
        persistence.restrict_permissions(
            Path("config"),
            is_windows=True,
            windows_acl=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                WindowsTokenProbeError("probe")
            ),
            path_check=lambda _path: False,
        )

    monkeypatch.setattr(
        persistence,
        "restrict_posix_path_permissions",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("failed")),
    )
    assert (
        persistence.restrict_permissions(
            Path("config"),
            is_windows=False,
            path_check=lambda _path: False,
        )
        is False
    )
    with pytest.raises(ConfigurationError, match="could not be enforced"):
        persistence.restrict_permissions(
            Path("config"),
            is_windows=False,
            required=True,
            path_check=lambda _path: False,
        )
    monkeypatch.setattr(
        persistence,
        "restrict_posix_path_permissions",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            UnsafeFileError("permission target changed before mutation")
        ),
    )
    with pytest.raises(ConfigurationError, match="changed before mutation"):
        persistence.restrict_permissions(
            Path("config"),
            is_windows=False,
            path_check=lambda _path: False,
        )
    monkeypatch.setattr(
        persistence,
        "restrict_posix_path_permissions",
        lambda *_args, **_kwargs: None,
    )
    assert (
        persistence.restrict_permissions(
            Path("config"),
            is_windows=False,
            path_check=lambda _path: False,
        )
        is True
    )


def test_atomic_write_posix_fsync_and_directory_error_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        persistence,
        "assert_config_namespace",
        lambda _path, **_kwargs: None,
    )
    target = tmp_path / "config.yaml"
    restricted: list[Path] = []
    original_open = persistence.os.open
    original_fsync = persistence.os.fsync
    original_close = persistence.os.close

    def preflight_with_directory_fsync(_path: Path) -> None:
        monkeypatch.setattr(persistence.os, "open", lambda *_args: 919)
        monkeypatch.setattr(persistence.os, "fsync", lambda descriptor: None)
        monkeypatch.setattr(persistence.os, "close", lambda descriptor: None)

    persistence.atomic_write_yaml(
        target,
        {"profile": "standard"},
        ensure_parent=lambda path: path.parent.mkdir(parents=True, exist_ok=True),
        restrict=lambda path, **_kwargs: restricted.append(path) or True,
        preflight=preflight_with_directory_fsync,
        path_check=lambda _path: False,
        is_windows=False,
    )
    assert target.exists()
    assert target in restricted

    monkeypatch.setattr(persistence.os, "open", original_open)
    monkeypatch.setattr(persistence.os, "fsync", original_fsync)
    monkeypatch.setattr(persistence.os, "close", original_close)

    def preflight_with_directory_failure(_path: Path) -> None:
        monkeypatch.setattr(
            persistence.os,
            "open",
            lambda *_args: (_ for _ in ()).throw(OSError("directory unavailable")),
        )

    persistence.atomic_write_yaml(
        target,
        {"profile": "power"},
        ensure_parent=lambda path: path.parent.mkdir(parents=True, exist_ok=True),
        restrict=lambda *_args, **_kwargs: True,
        preflight=preflight_with_directory_failure,
        path_check=lambda _path: False,
        is_windows=False,
    )
    assert "power" in target.read_text(encoding="utf-8")


def test_atomic_write_rejects_oversized_document(tmp_path: Path) -> None:
    with pytest.raises(ConfigValidationError, match="size limit"):
        persistence.atomic_write_yaml(
            tmp_path / "config.yaml",
            {"value": "x" * (MAX_CONFIG_BYTES + 1)},
            ensure_parent=lambda _path: None,
            restrict=lambda *_args, **_kwargs: True,
            preflight=lambda _path: None,
            path_check=lambda _path: False,
        )


def test_atomic_write_without_fchmod_remains_portable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delattr(persistence.os, "fchmod", raising=False)
    target = tmp_path / "portable.yaml"
    persistence.atomic_write_yaml(
        target,
        {"profile": "standard"},
        ensure_parent=lambda path: path.parent.mkdir(parents=True, exist_ok=True),
        restrict=lambda *_args, **_kwargs: True,
        preflight=lambda _path: None,
        path_check=lambda _path: False,
        is_windows=True,
    )
    assert target.exists()


def test_windows_atomic_write_retries_transient_reader_share_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "windows-retry.yaml"
    real_replace = persistence.os.replace
    attempts = 0
    delays: list[float] = []

    def replace(source: Path, destination: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("simulated Windows reader share lock")
        real_replace(source, destination)

    monkeypatch.setattr(persistence.os, "replace", replace)
    monkeypatch.setattr(persistence.time, "sleep", delays.append)

    persistence.atomic_write_yaml(
        target,
        {"profile": "standard"},
        ensure_parent=lambda path: path.parent.mkdir(parents=True, exist_ok=True),
        restrict=lambda *_args, **_kwargs: True,
        preflight=lambda _path: None,
        path_check=lambda _path: False,
        is_windows=True,
    )

    assert attempts == 3
    assert delays == [0.002, 0.004]
    assert target.exists()


def test_windows_atomic_write_preserves_replace_error_after_bounded_retries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "windows-retry-exhausted.yaml"
    delays: list[float] = []
    monkeypatch.setattr(
        persistence.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(PermissionError("still locked")),
    )
    monkeypatch.setattr(persistence.time, "sleep", delays.append)

    with pytest.raises(PermissionError, match="still locked"):
        persistence.atomic_write_yaml(
            target,
            {"profile": "standard"},
            ensure_parent=lambda path: path.parent.mkdir(parents=True, exist_ok=True),
            restrict=lambda *_args, **_kwargs: True,
            preflight=lambda _path: None,
            path_check=lambda _path: False,
            is_windows=True,
        )

    assert delays == list(persistence._WINDOWS_REPLACE_RETRY_DELAYS)
    assert list(tmp_path.glob(".windows-retry-exhausted.yaml.*.tmp")) == []


def test_config_lock_open_link_and_posix_lock_branches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        persistence,
        "assert_config_namespace",
        lambda _path, **_kwargs: None,
    )
    target = tmp_path / "config.yaml"
    monkeypatch.setattr(
        persistence.os,
        "open",
        lambda *_args: (_ for _ in ()).throw(OSError("denied")),
    )
    with (
        pytest.raises(ConfigLockError, match="opened safely"),
        persistence.config_lock(
            target,
            ensure_parent=lambda _path: None,
            restrict=lambda *_args, **_kwargs: True,
            path_check=lambda _path: False,
        ),
    ):
        pass

    monkeypatch.undo()
    monkeypatch.setattr(
        persistence,
        "assert_config_namespace",
        lambda _path, **_kwargs: None,
    )
    checks = iter((False, True))
    with (
        pytest.raises(ConfigLockError, match="symlink or non-regular"),
        persistence.config_lock(
            target,
            ensure_parent=lambda _path: None,
            restrict=lambda *_args, **_kwargs: True,
            path_check=lambda _path: next(checks),
        ),
    ):
        pass

    fake_fcntl = SimpleNamespace(
        LOCK_EX=1,
        LOCK_NB=2,
        LOCK_UN=4,
        calls=[],
    )
    fake_fcntl.flock = lambda descriptor, operation: fake_fcntl.calls.append(
        (descriptor, operation)
    )
    monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
    with persistence.config_lock(
        target,
        ensure_parent=lambda _path: None,
        restrict=lambda *_args, **_kwargs: True,
        path_check=lambda _path: False,
        is_windows=False,
    ):
        assert target.with_name(f".{target.name}.lock").exists()
    assert len(fake_fcntl.calls) == 2

    failing_fcntl = SimpleNamespace(
        LOCK_EX=1,
        LOCK_NB=2,
        LOCK_UN=4,
        flock=lambda *_args: (_ for _ in ()).throw(OSError("busy")),
    )
    monkeypatch.setitem(sys.modules, "fcntl", failing_fcntl)
    with (
        pytest.raises(ConfigLockError, match="configuration is busy"),
        persistence.config_lock(
            target,
            timeout=0,
            ensure_parent=lambda _path: None,
            restrict=lambda *_args, **_kwargs: True,
            path_check=lambda _path: False,
            is_windows=False,
        ),
    ):
        pass


def test_config_lock_windows_fallback_without_fchmod(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[int, int, int]] = []
    fake_msvcrt = SimpleNamespace(
        LK_NBLCK=1,
        LK_UNLCK=2,
        locking=lambda descriptor, mode, count: calls.append((descriptor, mode, count)),
    )
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    monkeypatch.delattr(persistence.os, "fchmod", raising=False)
    monkeypatch.delattr(persistence.os, "O_BINARY", raising=False)
    monkeypatch.delattr(persistence.os, "O_NOFOLLOW", raising=False)
    restricted: list[Path] = []
    target = tmp_path / "config.yaml"
    with persistence.config_lock(
        target,
        ensure_parent=lambda _path: None,
        restrict=lambda path, **_kwargs: restricted.append(path) or True,
        path_check=lambda _path: False,
        is_windows=True,
    ):
        pass
    assert len(calls) == 2
    assert restricted == [target.with_name(f".{target.name}.lock")]


def test_config_lock_applies_nofollow_when_the_platform_exposes_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        persistence,
        "assert_config_namespace",
        lambda _path, **_kwargs: None,
    )
    nofollow = 0x40000000
    captured: list[int] = []
    real_open = persistence.os.open

    def open_without_synthetic_flag(path: Path, flags: int, mode: int) -> int:
        captured.append(flags)
        return real_open(path, flags & ~nofollow, mode)

    fake_fcntl = SimpleNamespace(
        LOCK_EX=1,
        LOCK_NB=2,
        LOCK_UN=4,
        flock=lambda *_args: None,
    )
    monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
    monkeypatch.setattr(persistence.os, "O_NOFOLLOW", nofollow, raising=False)
    monkeypatch.setattr(persistence.os, "open", open_without_synthetic_flag)
    target = tmp_path / "config.yaml"

    with persistence.config_lock(
        target,
        ensure_parent=lambda path: path.parent.mkdir(parents=True, exist_ok=True),
        restrict=lambda *_args, **_kwargs: True,
        path_check=lambda _path: False,
        is_windows=False,
    ):
        pass

    assert captured and captured[0] & nofollow


def test_config_lock_posix_fallback_without_fchmod(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        persistence,
        "assert_config_namespace",
        lambda _path, **_kwargs: None,
    )
    calls: list[tuple[int, int]] = []
    fake_fcntl = SimpleNamespace(
        LOCK_EX=1,
        LOCK_NB=2,
        LOCK_UN=4,
        flock=lambda descriptor, operation: calls.append((descriptor, operation)),
    )
    monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
    monkeypatch.delattr(persistence.os, "fchmod", raising=False)
    target = tmp_path / "config.yaml"
    with persistence.config_lock(
        target,
        ensure_parent=lambda _path: None,
        restrict=lambda *_args, **_kwargs: True,
        path_check=lambda _path: False,
        is_windows=False,
    ):
        pass
    assert len(calls) == 2


def test_schema_litellm_field_loop_completes_after_skip_models() -> None:
    assert schema._validate_adapter_entry(
        {"skip_models": ["router"], "enabled": "auto"}, "litellm"
    ) == {"skip_models": ["router"], "enabled": "auto"}


def test_secret_presence_ignores_nonmapping_provider_entries() -> None:
    assert service._secret_presence({"providers": [None, {}]}) == {"providers.1.api_key": False}


def test_environment_override_validation_and_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENCY_JUDGE_TIMEOUT", "invalid")
    with pytest.raises(ConfigValidationError, match="AGENCY_JUDGE_TIMEOUT"):
        service._environment_overrides()
    monkeypatch.setenv("AGENCY_JUDGE_TIMEOUT", "nan")
    with pytest.raises(ConfigValidationError, match="AGENCY_JUDGE_TIMEOUT"):
        service._environment_overrides()
    monkeypatch.delenv("AGENCY_JUDGE_TIMEOUT")
    monkeypatch.setenv("AGENCY_CAPTURE_CONTENT", "sometimes")
    with pytest.raises(ConfigValidationError, match="AGENCY_CAPTURE_CONTENT"):
        service._environment_overrides()
    monkeypatch.delenv("AGENCY_CAPTURE_CONTENT")
    monkeypatch.delenv("AGENCY_JUDGE_API_KEY", raising=False)
    monkeypatch.setenv("LITELLM_API_KEY", "secret")
    assert service._environment_overrides()["judge.api_key"] == "LITELLM_API_KEY"


def test_effective_document_sanitizes_loader_and_validation_failures() -> None:
    with pytest.raises(ConfigValidationError, match="could not be loaded"):
        service.effective_document(
            Path("config"),
            load=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("secret")),
            render=lambda *_args, **_kwargs: "{}",
            validate=lambda value: dict(value),
        )
    with pytest.raises(ConfigValidationError, match="effective configuration is invalid"):
        service.effective_document(
            Path("config"),
            load=lambda **_kwargs: object(),
            render=lambda *_args, **_kwargs: "[1]",
            validate=lambda value: dict(value),
        )
    with pytest.raises(ConfigValidationError, match="invalid override"):
        service.effective_document(
            Path("config"),
            load=lambda **_kwargs: object(),
            render=lambda *_args, **_kwargs: "{}",
            validate=lambda _value: (_ for _ in ()).throw(ConfigValidationError("bad")),
        )


def test_configuration_transactions_cover_conflict_and_contract_errors() -> None:
    reads = iter([({}, b"a"), ({}, b"b")] * 3)
    with pytest.raises(ConfigConflictError, match="changed while"):
        service.read_config_state(
            None,
            resolve_path=lambda _path: Path("config"),
            read_document=lambda _path: next(reads),
            validate=lambda value: dict(value),
            project=lambda *_args: object(),  # type: ignore[arg-type]
        )

    with pytest.raises(ConfigValidationError, match="expected revision"):
        service.apply_config_operations(
            [{}],
            expected_revision="invalid",
            path=None,
            validate_batch=lambda _operations: None,
            resolve_path=lambda _path: Path("config"),
            lock=lambda _path: nullcontext(),
            read_document=lambda _path: ({}, b""),
            revision=lambda _raw: "sha256:value",
            validate=lambda value: dict(value),
            apply=lambda document, _operations: (document, set(), False),
            complete=lambda *_args, **_kwargs: object(),  # type: ignore[arg-type]
        )

    common = {
        "path": None,
        "recover_invalid_existing": False,
        "resolve_path": lambda _path: Path("config"),
        "lock": lambda _path: nullcontext(),
        "read_raw": lambda _path: b"raw",
        "revision": lambda _raw: "sha256:actual",
        "parse": lambda _raw: {},
        "validate": lambda value: dict(value),
        "enforce_policy": lambda _document: False,
        "diff_paths": lambda _before, _after: set(),
        "complete": lambda *_args, **_kwargs: object(),
    }
    with pytest.raises(ConfigValidationError, match="root must be a mapping"):
        service.replace_config_document([], expected_revision="sha256:actual", **common)  # type: ignore[arg-type]
    with pytest.raises(ConfigValidationError, match="expected revision"):
        service.replace_config_document({}, expected_revision="invalid", **common)
    with pytest.raises(ConfigConflictError, match="configuration changed"):
        service.replace_config_document({}, expected_revision="sha256:stale", **common)
