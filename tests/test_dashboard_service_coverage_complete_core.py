"""Boundary and subprocess coverage for dashboard service primitives."""

from __future__ import annotations

import io
import os
import subprocess
from dataclasses import replace
from types import SimpleNamespace

import pytest

from agency_runtime.core import dashboard_runtime
from agency_runtime.core import dashboard_service_core as subject
from agency_runtime.core.process_argv import agency_bootstrap_path
from tests.runtime_support import trusted_base_test_interpreter


def test_command_result_terminal_safety_and_public_shape():
    success = subject._CommandResult(("manager",), 0, "ok", "")
    assert success.ok and success.public() == {
        "command": ["manager"],
        "returncode": 0,
        "ok": True,
    }
    failure = subject._CommandResult(("manager",), 2, "fallback", "bad\x00detail")
    assert failure.public()["error"] == "bad?detail"
    assert failure.public(include_failure_output=False)["error"] == (
        "service-manager command failed"
    )
    assert subject._CommandResult(("manager",), 1).public()["error"] == (
        "service-manager command failed"
    )


def test_dashboard_runtime_generation_helpers_are_fail_closed(tmp_path, monkeypatch):
    ctx = subject._context(
        home_dir=tmp_path,
        platform_name="linux",
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
    )
    assert ctx is not None
    assert subject._dashboard_runtime_fingerprint(ctx) is None
    assert subject._cleanup_stale_dashboard_runtime(ctx) is False
    assert subject._dashboard_runtime_cleared(ctx) is True
    assert subject._fresh_dashboard_readiness(ctx, None, None) is None
    assert subject._fresh_dashboard_readiness(ctx, None, "prior") is False

    def failed_probe():
        raise RuntimeError("probe failed")

    assert subject._fresh_dashboard_readiness(ctx, failed_probe, None) is False
    assert subject._fresh_dashboard_readiness(ctx, lambda: False, None) is False
    assert subject._fresh_dashboard_readiness(ctx, lambda: True, None) is True

    dashboard_runtime.write_dashboard_runtime(
        home_dir=tmp_path,
        token="first-generation-" + ("a" * 32),
        port=7810,
        pid=111,
    )
    first = subject._dashboard_runtime_fingerprint(ctx)
    assert first is not None
    assert subject._dashboard_runtime_port(ctx) == 7810
    monkeypatch.setattr(dashboard_runtime, "dashboard_service_reachable", lambda **_kw: True)
    assert subject._cleanup_stale_dashboard_runtime(ctx) is False
    assert subject._dashboard_runtime_cleared(ctx) is False
    assert subject._fresh_dashboard_readiness(ctx, lambda: True, first) is False

    dashboard_runtime.write_dashboard_runtime(
        home_dir=tmp_path,
        token="second-generation-" + ("b" * 32),
        port=7810,
        pid=111,
    )
    second = subject._dashboard_runtime_fingerprint(ctx)
    assert second is not None
    assert subject._dashboard_runtime_cleared(ctx) is False
    assert subject._fresh_dashboard_readiness(ctx, lambda: True, first) is True

    monkeypatch.setattr(dashboard_runtime, "dashboard_service_reachable", lambda **_kw: False)
    assert subject._cleanup_stale_dashboard_runtime(ctx, expected_fingerprint=first) is False
    assert subject._dashboard_runtime_fingerprint(ctx) == second
    assert subject._cleanup_stale_dashboard_runtime(ctx, expected_fingerprint=second) is True
    assert subject._dashboard_runtime_cleared(ctx) is True

    runtime_path = dashboard_runtime.dashboard_runtime_path(home_dir=tmp_path)
    runtime_path.write_text("{}", encoding="utf-8")
    assert subject._dashboard_runtime_fingerprint(ctx) is None
    assert subject._cleanup_stale_dashboard_runtime(ctx) is False
    assert subject._dashboard_runtime_cleared(ctx) is False
    assert subject._fresh_dashboard_readiness(ctx, lambda: True, first) is False


def test_dashboard_runtime_clearance_wait_retries_identity_safe_cleanup(
    tmp_path,
    monkeypatch,
):
    ctx = subject._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
    )
    assert ctx is not None
    cleanup_results = iter((False, True))
    clearance_calls = []
    sleeps = []
    monkeypatch.setattr(
        subject,
        "_cleanup_stale_dashboard_runtime",
        lambda _ctx, **_kwargs: next(cleanup_results),
    )
    monkeypatch.setattr(
        subject,
        "_dashboard_runtime_fingerprint",
        lambda _ctx: "sha256:old",
    )

    def clearance(_ctx):
        clearance_calls.append("clearance")
        return len(clearance_calls) == 2

    monkeypatch.setattr(subject, "_dashboard_runtime_cleared", clearance)
    monkeypatch.setattr(subject.time, "sleep", sleeps.append)

    outcome = subject._wait_dashboard_runtime_cleared(
        ctx,
        "sha256:old",
        timeout_seconds=1.0,
        poll_seconds=0.0,
    )
    assert outcome.cleared is True
    assert outcome.descriptor_removed is True
    assert outcome.replacement_detected is False
    assert clearance_calls == ["clearance", "clearance"]
    assert sleeps == [0.0]


def test_dashboard_runtime_clearance_wait_preserves_replacement(
    tmp_path,
    monkeypatch,
):
    ctx = subject._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
    )
    assert ctx is not None
    monkeypatch.setattr(
        subject,
        "_dashboard_runtime_fingerprint",
        lambda _ctx: "sha256:replacement",
    )
    monkeypatch.setattr(
        subject,
        "_cleanup_stale_dashboard_runtime",
        lambda *_args, **_kwargs: pytest.fail("replacement cleanup must not run"),
    )

    outcome = subject._wait_dashboard_runtime_cleared(
        ctx,
        "sha256:old",
        timeout_seconds=0.0,
    )
    assert outcome == subject._DashboardRuntimeClearance(
        cleared=False,
        descriptor_removed=False,
        replacement_detected=True,
    )
    no_prior = subject._wait_dashboard_runtime_cleared(
        ctx,
        None,
        timeout_seconds=0.0,
    )
    assert no_prior.replacement_detected is True


def test_dashboard_runtime_clearance_waits_for_the_old_listener_to_release(
    tmp_path,
    monkeypatch,
):
    ctx = subject._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
    )
    assert ctx is not None
    listener_states = iter((True, False))
    listener_calls = []
    sleeps = []
    monkeypatch.setattr(subject, "_dashboard_runtime_fingerprint", lambda _ctx: None)
    monkeypatch.setattr(subject, "_dashboard_runtime_cleared", lambda _ctx: True)
    monkeypatch.setattr(
        subject,
        "_loopback_listener_present",
        lambda port: listener_calls.append(port) or next(listener_states),
    )
    monkeypatch.setattr(subject.time, "sleep", sleeps.append)

    outcome = subject._wait_dashboard_runtime_cleared(
        ctx,
        "sha256:old",
        previous_port=7810,
        timeout_seconds=1.0,
        poll_seconds=0.0,
    )

    assert outcome == subject._DashboardRuntimeClearance(True, False)
    assert listener_calls == [7810, 7810]
    assert sleeps == [0.0]


def test_dashboard_runtime_clearance_wait_fails_closed_at_deadline(
    tmp_path,
    monkeypatch,
):
    ctx = subject._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
    )
    assert ctx is not None
    monkeypatch.setattr(subject, "_cleanup_stale_dashboard_runtime", lambda _ctx: False)
    monkeypatch.setattr(subject, "_dashboard_runtime_fingerprint", lambda _ctx: None)
    monkeypatch.setattr(
        subject,
        "_dashboard_runtime_cleared",
        lambda *_args, **_kwargs: False,
    )

    outcome = subject._wait_dashboard_runtime_cleared(
        ctx,
        "sha256:still-live",
        timeout_seconds=0.0,
    )
    assert outcome == subject._DashboardRuntimeClearance(
        cleared=False,
        descriptor_removed=False,
    )


@pytest.mark.parametrize("value", ["", "bad\x00value"])
def test_validate_text_rejects_empty_and_control_values(value):
    with pytest.raises(ValueError):
        subject._validate_text(value, label="value")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Windows", "windows"),
        ("WIN32", "windows"),
        ("nt", "windows"),
        ("Linux", "linux"),
        ("GNU/Linux", "linux"),
        ("Darwin", "darwin"),
    ],
)
def test_platform_normalization(value, expected):
    assert subject._normalise_platform(value) == expected


def test_config_path_precedence_and_worker_argv(tmp_path, monkeypatch):
    home = tmp_path / "home"
    explicit = tmp_path / "explicit.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "environment.yaml"))
    assert subject._config_path(home, None, explicit) == explicit.resolve()
    assert subject._config_path(home, None, None) == (tmp_path / "environment.yaml").resolve()
    assert (
        subject._config_path(home, home, None)
        == (home / ".agency-runtime" / "agency.yaml").resolve()
    )
    argv = subject.build_service_worker_argv(
        home_dir=home,
        config_path=explicit,
        python_executable=tmp_path / "python",
    )
    assert argv == [
        str((tmp_path / "python").resolve()),
        "-I",
        "-S",
        agency_bootstrap_path(),
        "agency_runtime.server.dashboard_service",
        "--config",
        str(explicit.resolve()),
    ]


def test_service_environment_override_detection_is_names_only_and_allows_config_path():
    config = SimpleNamespace(
        judge=SimpleNamespace(api_key_env="CUSTOM_JUDGE_KEY"),
        providers=(SimpleNamespace(api_key_env="CUSTOM_PROVIDER_KEY"),),
        adapters=SimpleNamespace(
            litellm=SimpleNamespace(api_key_env="LITELLM_API_KEY"),
            hermes=SimpleNamespace(api_key_env=""),
            openclaw=SimpleNamespace(api_key_env=""),
            codex=SimpleNamespace(api_key_env=""),
            claude=SimpleNamespace(api_key_env=""),
        ),
    )
    environment = {
        "AGENCY_CONFIG_PATH": "durable/config.yaml",
        "AGENCY_DB_PATH": "process-only.db",
        "AGENCY_JUDGE_API_KEY": "top-secret-value",
        "CUSTOM_JUDGE_KEY": "another-secret-value",
        "CUSTOM_PROVIDER_KEY": "",
    }

    names = subject.dashboard_service_environment_overrides(config, environ=environment)
    diagnostic = subject.dashboard_service_environment_error(names)

    assert names == ("AGENCY_DB_PATH", "AGENCY_JUDGE_API_KEY", "CUSTOM_JUDGE_KEY")
    assert "AGENCY_CONFIG_PATH" not in names
    assert "top-secret-value" not in diagnostic
    assert "another-secret-value" not in diagnostic
    assert all(name in diagnostic for name in names)


def test_context_unsupported_windows_linux_and_xdg(tmp_path, monkeypatch):
    assert (
        subject._context(
            home_dir=tmp_path,
            platform_name="darwin",
            config_path=None,
            python_executable=tmp_path / "python",
        )
        is None
    )
    monkeypatch.setattr(subject, "_IS_WINDOWS", True)
    monkeypatch.setattr(subject, "_windows_current_user_sid", lambda: "S-1-5-test")
    monkeypatch.setattr(subject, "_windows_account_for_sid", lambda _sid: "DOMAIN\\user")
    windows = subject._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=None,
        python_executable=tmp_path / "python",
    )
    assert windows is not None
    assert windows.manager == "schtasks" and windows.windows_user == "S-1-5-test"
    assert windows.windows_account == "DOMAIN\\user"
    monkeypatch.setattr(subject, "_IS_WINDOWS", False)
    monkeypatch.setattr(subject, "_windows_current_user_sid", lambda: None)
    monkeypatch.setenv("USERNAME", "user")
    monkeypatch.setenv("USERDOMAIN", "DOMAIN")
    windows = subject._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=None,
        python_executable=tmp_path / "python",
    )
    assert windows is not None and windows.windows_user == "DOMAIN\\user"
    assert windows.windows_account == "DOMAIN\\user"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    linux = subject._context(
        home_dir=None,
        platform_name="linux",
        config_path=tmp_path / "config.yaml",
        python_executable=tmp_path / "python",
    )
    assert linux is not None and linux.unit_path == (
        tmp_path / "xdg" / "systemd" / "user" / subject.SYSTEMD_UNIT_NAME
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", "relative")
    monkeypatch.setattr(subject.Path, "home", lambda: tmp_path)
    linux = subject._context(
        home_dir=None,
        platform_name="linux",
        config_path=None,
        python_executable=tmp_path / "python",
    )
    assert linux is not None and linux.unit_path == (
        tmp_path / ".config" / "systemd" / "user" / subject.SYSTEMD_UNIT_NAME
    )


def test_native_linux_launcher_platform_and_short_worker_fail_closed(
    tmp_path,
    monkeypatch,
    os_facade,
):
    ctx = subject._context(
        home_dir=tmp_path,
        platform_name="linux",
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
    )
    assert ctx is not None
    monkeypatch.setattr(subject, "os", os_facade(subject.os, name="posix"))
    monkeypatch.setattr(subject.platform, "system", lambda: "Linux")
    assert subject._native_launcher_platform(ctx) == "posix"

    monkeypatch.setattr(subject, "_native_launcher_platform", lambda _ctx: "posix")
    with pytest.raises(OSError, match="isolated bootstrap"):
        subject._validate_dashboard_launcher(replace(ctx, worker_argv=("python", "-I")))


def test_native_windows_launcher_platform_is_detected_portably(
    tmp_path,
    monkeypatch,
    os_facade,
):
    ctx = subject._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python.exe",
    )
    assert ctx is not None
    monkeypatch.setattr(subject, "os", os_facade(subject.os, name="nt"))

    assert subject._native_launcher_platform(ctx) == "nt"


def test_dashboard_launcher_projects_complete_private_runtime_then_rechecks(
    tmp_path,
    monkeypatch,
):
    ctx = subject._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python.exe",
    )
    assert ctx is not None
    monkeypatch.setattr(subject, "_native_launcher_platform", lambda _ctx: "nt")
    python_identity = SimpleNamespace(lexical_path=ctx.worker_argv[0])
    private = str(tmp_path / "private-bootstrap.py")
    bootstrap_identity = SimpleNamespace(lexical_path=private)
    monkeypatch.setattr(
        subject,
        "prepare_private_package_runtime",
        lambda path: private if path == ctx.worker_argv[3] else "",
    )
    monkeypatch.setattr(
        subject,
        "_probe_python_cache_tag",
        lambda identity, **_kwargs: (
            "cpython-test"
            if identity is python_identity
            else pytest.fail("unexpected Python identity")
        ),
    )

    def snapshot(paths, *, platform_name):
        assert platform_name == "nt"
        assert paths == (ctx.worker_argv[0],)
        return (python_identity,)

    monkeypatch.setattr(subject, "snapshot_persistent_artifacts", snapshot)
    monkeypatch.setattr(
        subject,
        "snapshot_persistent_artifact",
        lambda path, **_kwargs: (
            bootstrap_identity if path == private else pytest.fail("unexpected bootstrap path")
        ),
    )
    revalidated: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        subject,
        "revalidate_persistent_artifacts",
        lambda identities, **_kwargs: revalidated.append(tuple(identities)),
    )

    validated = subject._validate_dashboard_launcher(ctx)

    assert validated.worker_argv[3] == private
    assert validated.launcher_artifacts == (python_identity, bootstrap_identity)
    assert revalidated == [(python_identity, bootstrap_identity)]


def test_dashboard_launcher_rejects_wrong_python_before_projecting_runtime(
    tmp_path,
    monkeypatch,
):
    explicit = r"C:\Python312\python.exe"
    ctx = subject._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=tmp_path / "agency.yaml",
        python_executable=explicit,
    )
    assert ctx is not None
    identity = SimpleNamespace(lexical_path=explicit)
    monkeypatch.setattr(subject, "_native_launcher_platform", lambda _ctx: "nt")
    monkeypatch.setattr(
        subject,
        "snapshot_persistent_artifacts",
        lambda paths, **_kwargs: (identity,) if paths == (explicit,) else (),
    )
    monkeypatch.setattr(
        subject,
        "_probe_python_cache_tag",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OSError(
                "selected dashboard Python cache tag does not match the Agency Runtime interpreter"
            )
        ),
    )
    monkeypatch.setattr(
        subject,
        "prepare_private_package_runtime",
        lambda _path: pytest.fail("wrong-interpreter validation created a runtime projection"),
    )

    with pytest.raises(OSError, match="does not match"):
        subject._validate_dashboard_launcher(ctx)


def test_python_cache_tag_probe_accepts_only_exact_current_interpreter(
    monkeypatch,
):
    identity = SimpleNamespace(lexical_path=r"C:\Python313\python.exe")
    revalidated: list[tuple[object, ...]] = []
    monkeypatch.setattr(subject, "current_python_cache_tag", lambda: "cpython-313")
    monkeypatch.setattr(
        subject,
        "revalidate_persistent_artifacts",
        lambda identities, **_kwargs: revalidated.append(tuple(identities)),
    )

    def run(argv, **kwargs):
        assert argv == (
            identity.lexical_path,
            "-I",
            "-S",
            "-c",
            subject._PYTHON_CACHE_TAG_PROBE_SOURCE,
        )
        assert kwargs["timeout"] == subject._PYTHON_CACHE_TAG_PROBE_TIMEOUT_SECONDS
        assert kwargs["check"] is False
        assert kwargs["shell"] is False
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert kwargs["stderr"] is subprocess.DEVNULL
        kwargs["stdout"].write(b"cpython-313")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subject.subprocess, "run", run)

    assert subject._probe_python_cache_tag(identity, platform_name="nt") == "cpython-313"
    assert revalidated == [(identity,), (identity,)]


def test_python_cache_tag_probe_accepts_the_real_current_interpreter():
    identity = subject.snapshot_persistent_artifact(
        trusted_base_test_interpreter(),
        platform_name=os.name,
        require_executable=True,
    )

    assert subject._probe_python_cache_tag(identity, platform_name=os.name) == (
        subject.current_python_cache_tag()
    )


def test_python_cache_tag_probe_rejects_an_explicit_foreign_interpreter(
    monkeypatch,
):
    identity = SimpleNamespace(lexical_path=r"C:\Python312\python.exe")
    monkeypatch.setattr(subject, "current_python_cache_tag", lambda: "cpython-313")
    monkeypatch.setattr(subject, "revalidate_persistent_artifacts", lambda *_args, **_kwargs: None)

    def run(_argv, **kwargs):
        kwargs["stdout"].write(b"cpython-312")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subject.subprocess, "run", run)

    with pytest.raises(OSError, match="does not match"):
        subject._probe_python_cache_tag(identity, platform_name="nt")


@pytest.mark.parametrize(
    ("payload", "returncode", "message"),
    [
        (b"cpython-313\n", 0, "does not match"),
        (b"x" * 129, 0, "does not match"),
        (b"cpython-313", 7, "probe failed"),
    ],
)
def test_python_cache_tag_probe_rejects_malformed_oversized_and_nonzero_output(
    monkeypatch,
    payload,
    returncode,
    message,
):
    identity = SimpleNamespace(lexical_path=r"C:\Python313\python.exe")
    monkeypatch.setattr(subject, "current_python_cache_tag", lambda: "cpython-313")
    monkeypatch.setattr(subject, "revalidate_persistent_artifacts", lambda *_args, **_kwargs: None)

    def run(_argv, **kwargs):
        kwargs["stdout"].write(payload)
        return SimpleNamespace(returncode=returncode)

    monkeypatch.setattr(subject.subprocess, "run", run)

    with pytest.raises(OSError, match=message):
        subject._probe_python_cache_tag(identity, platform_name="nt")


def test_python_cache_tag_probe_rejects_timeout_after_final_identity_check(
    monkeypatch,
):
    identity = SimpleNamespace(lexical_path=r"C:\Python313\python.exe")
    revalidated: list[tuple[object, ...]] = []
    monkeypatch.setattr(subject, "current_python_cache_tag", lambda: "cpython-313")
    monkeypatch.setattr(
        subject,
        "revalidate_persistent_artifacts",
        lambda identities, **_kwargs: revalidated.append(tuple(identities)),
    )
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda argv, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(argv, kwargs["timeout"])
        ),
    )

    with pytest.raises(OSError, match="timed out"):
        subject._probe_python_cache_tag(identity, platform_name="nt")
    assert revalidated == [(identity,), (identity,)]


def test_python_cache_tag_probe_rejects_post_probe_executable_drift(
    monkeypatch,
):
    identity = SimpleNamespace(lexical_path=r"C:\Python313\python.exe")
    revalidation_count = 0
    monkeypatch.setattr(subject, "current_python_cache_tag", lambda: "cpython-313")

    def revalidate(_identities, **_kwargs):
        nonlocal revalidation_count
        revalidation_count += 1
        if revalidation_count == 2:
            raise OSError("persistent executable artifact drifted")

    def run(_argv, **kwargs):
        kwargs["stdout"].write(b"cpython-313")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subject, "revalidate_persistent_artifacts", revalidate)
    monkeypatch.setattr(subject.subprocess, "run", run)

    with pytest.raises(OSError, match="artifact drifted"):
        subject._probe_python_cache_tag(identity, platform_name="nt")
    assert revalidation_count == 2


def test_installed_dashboard_launcher_is_read_only_and_exact(
    tmp_path,
    monkeypatch,
):
    ctx = subject._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python.exe",
    )
    assert ctx is not None
    monkeypatch.setattr(subject, "_native_launcher_platform", lambda _ctx: "nt")
    private = str(tmp_path / "published" / "_bootstrap.py")
    worker = [*ctx.worker_argv]
    worker[3] = private
    verified: list[str] = []
    identity = SimpleNamespace()
    monkeypatch.setattr(
        subject,
        "verify_private_package_runtime",
        lambda path: verified.append(path) or path,
    )
    monkeypatch.setattr(
        subject,
        "prepare_private_package_runtime",
        lambda _path: pytest.fail("read-only inspection attempted projection creation"),
    )
    monkeypatch.setattr(
        subject,
        "snapshot_persistent_artifacts",
        lambda paths, **_kwargs: (identity,) if paths == (worker[0], private) else (),
    )

    validated = subject._validate_installed_dashboard_launcher(ctx, worker)

    assert verified == [private]
    assert validated.worker_argv == tuple(worker)
    assert validated.launcher_artifacts == (identity,)

    for invalid in (None, worker[:3], [*worker[:4], "wrong.module", *worker[5:]]):
        with pytest.raises(OSError, match="invalid worker command"):
            subject._validate_installed_dashboard_launcher(ctx, invalid)


def test_windows_sid_non_windows_and_library_failure(monkeypatch):
    import ctypes

    monkeypatch.setattr(subject, "_IS_WINDOWS", False)
    assert subject._windows_current_user_sid() is None
    monkeypatch.setattr(subject, "_IS_WINDOWS", True)

    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("missing")),
        raising=False,
    )
    assert subject._windows_current_user_sid() is None
    assert subject._windows_account_for_sid("S-1-5-test") is None


def test_native_windows_context_requires_token_bound_account(tmp_path, monkeypatch):
    monkeypatch.setattr(subject, "_IS_WINDOWS", True)
    monkeypatch.setattr(subject, "_windows_current_user_sid", lambda: None)
    with pytest.raises(RuntimeError, match="token identity"):
        subject._context(
            home_dir=tmp_path,
            platform_name="windows",
            config_path=None,
            python_executable=tmp_path / "python",
        )

    monkeypatch.delenv("USERNAME", raising=False)
    monkeypatch.delenv("USERDOMAIN", raising=False)
    monkeypatch.setattr(
        subject.getpass,
        "getuser",
        lambda: (_ for _ in ()).throw(RuntimeError("environment unavailable")),
    )
    monkeypatch.setattr(subject, "_windows_current_user_sid", lambda: "S-1-5-test")
    monkeypatch.setattr(subject, "_windows_account_for_sid", lambda _sid: "DOMAIN\\user")
    native = subject._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=None,
        python_executable=tmp_path / "python",
    )
    assert native is not None and native.windows_account == "DOMAIN\\user"

    monkeypatch.setattr(subject, "_windows_account_for_sid", lambda _sid: None)
    with pytest.raises(RuntimeError, match="token identity"):
        subject._context(
            home_dir=tmp_path,
            platform_name="windows",
            config_path=None,
            python_executable=tmp_path / "python",
        )


def test_service_worker_preserves_virtualenv_python_symlink(tmp_path):
    interpreter = tmp_path / "python3.12"
    interpreter.write_bytes(b"python")
    virtualenv_python = tmp_path / ".venv" / "bin" / "python"
    virtualenv_python.parent.mkdir(parents=True)
    try:
        virtualenv_python.symlink_to(interpreter)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable on this host: {exc}")

    argv = subject.build_service_worker_argv(
        home_dir=tmp_path / "home",
        python_executable=virtualenv_python,
    )

    assert argv[0] == str(virtualenv_python.absolute())
    assert argv[0] != str(interpreter.resolve())


def test_bounded_text_and_stream_cover_bytes_strings_and_limits(monkeypatch):
    monkeypatch.setattr(subject, "_MAX_MANAGER_OUTPUT_BYTES", 4)
    assert subject._bounded_text(b"abc") == ("abc", False)
    assert subject._bounded_text("abcdef") == ("abcd", True)
    stream = io.BytesIO(b"abcdef")
    stream.seek(3)
    assert subject._read_command_stream(stream) == ("abcd", True)


def test_invoke_runner_supports_timeout_legacy_and_uninspectable(monkeypatch):
    calls = []

    def modern(argv, *, timeout):
        calls.append((argv, timeout))
        return "modern"

    def legacy(argv):
        calls.append(argv)
        return "legacy"

    assert subject._invoke_runner(modern, ("one",), timeout=2) == "modern"
    assert subject._invoke_runner(legacy, ("two",), timeout=3) == "legacy"
    monkeypatch.setattr(
        subject.inspect,
        "signature",
        lambda _runner: (_ for _ in ()).throw(ValueError("opaque")),
    )
    assert subject._invoke_runner(modern, ("three",), timeout=4) == "modern"


@pytest.mark.parametrize("value", [True, 1.5, "1", None])
def test_returncode_rejects_non_integer_values(value):
    with pytest.raises(TypeError):
        subject._coerce_returncode(value)


@pytest.mark.parametrize("value", [-(2**31) - 1, 2**31])
def test_returncode_rejects_out_of_range_values(value):
    with pytest.raises(ValueError):
        subject._coerce_returncode(value)


@pytest.mark.parametrize("timeout", [True, 0, -1, float("nan"), 301, "30"])
def test_run_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError, match="timeout"):
        subject._run(["manager"], command_runner=lambda _argv: None, timeout=timeout)


def test_run_rejects_empty_command():
    with pytest.raises(ValueError, match="must not be empty"):
        subject._run([], command_runner=None)


def test_run_normalizes_injected_result_shapes(monkeypatch):
    direct = subject._run(
        ["one"],
        command_runner=lambda _argv, **_kw: subject._CommandResult(("raw",), 2, "out", "err"),
    )
    assert direct.command == ("one",) and direct.returncode == 2
    mapped = subject._run(
        ["two"],
        command_runner=lambda _argv, **_kw: {
            "exit_code": 3,
            "stdout": b"out",
            "error": "err",
        },
    )
    assert (mapped.returncode, mapped.stdout, mapped.stderr) == (3, "out", "err")
    obj = SimpleNamespace(returncode=4, stdout="object", stderr="failure")
    normalized = subject._run(["three"], command_runner=lambda _argv, **_kw: obj)
    assert normalized.returncode == 4 and normalized.stdout == "object"
    monkeypatch.setattr(subject, "_MAX_MANAGER_OUTPUT_BYTES", 2)
    limited = subject._run(
        ["four"],
        command_runner=lambda _argv, **_kw: {"returncode": 0, "stdout": "long"},
    )
    assert limited.returncode == 125 and "exceeded" in limited.stderr


@pytest.mark.parametrize(
    ("failure", "code", "message"),
    [
        (subprocess.TimeoutExpired("manager", 1, output="partial"), 124, "timed out"),
        (OSError("offline"), 127, "OSError"),
        (TypeError("invalid"), 125, "invalid service-manager result"),
        (LookupError("unexpected"), 127, "runner failed: LookupError"),
    ],
)
def test_run_normalizes_runner_failures(failure, code, message):
    def fail(*_args, **_kwargs):
        raise failure

    result = subject._run(["manager"], command_runner=fail)
    assert result.returncode == code and message in result.stderr


def test_run_rejects_async_runner_and_closes_coroutine():
    async def async_result():
        return 0

    result = subject._run(["manager"], command_runner=lambda *_a, **_kw: async_result())
    assert result.returncode == 125 and "must be synchronous" not in result.stderr


def test_run_real_subprocess_success_and_inner_timeout(monkeypatch):
    monkeypatch.setattr(
        subject,
        "prepare_process_argv",
        lambda argv, **_kwargs: list(argv),
    )
    monkeypatch.setattr(subject, "freeze_process_argv", lambda argv, **_kwargs: argv)
    monkeypatch.setattr(subject, "revalidate_process_argv", lambda _argv: None)

    def success(_argv, *, stdout, stderr, **_kwargs):
        stdout.write(b"out")
        stderr.write(b"err")
        return SimpleNamespace(returncode=5)

    monkeypatch.setattr(subject.subprocess, "run", success)
    result = subject._run(["manager"], command_runner=None)
    assert (result.returncode, result.stdout, result.stderr) == (5, "out", "err")

    def timeout(_argv, *, stdout, **_kwargs):
        stdout.write(b"partial")
        raise subprocess.TimeoutExpired("manager", 1)

    monkeypatch.setattr(subject.subprocess, "run", timeout)
    result = subject._run(["manager"], command_runner=None)
    assert result.returncode == 124 and result.stdout == "partial"


def test_base_and_unsupported_payloads(tmp_path):
    ctx = subject._context(
        home_dir=tmp_path,
        platform_name="linux",
        config_path=None,
        python_executable=tmp_path / "python",
    )
    assert ctx is not None
    assert subject._base("inspect", ctx)["action"] == "inspect"
    unsupported = subject._unsupported("install", "darwin")
    assert unsupported["exit_code"] == 2 and unsupported["supported"] is False
