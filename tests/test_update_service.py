"""Security, caching, and immutable-target tests for update discovery."""

from __future__ import annotations

import json
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import update_service as subject

_MAIN_SHA = "b" * 40
_RELEASE_SHA = "c" * 40


def _installed(*, revision: str | None = "a" * 40, dirty: bool | None = False) -> dict[str, Any]:
    return {
        "package_version": "0.1.0",
        "build_identity": "0.1.0+gaaaaaaaaaaaa",
        "source_revision": revision,
        "source_branch": "main" if revision else None,
        "source_dirty": dirty,
        "install_kind": "source-checkout" if revision else "package",
        "official_repository": True,
    }


def _commit(sha: str) -> dict[str, str]:
    return {
        "sha": sha,
        "html_url": f"https://github.com/{subject.REPOSITORY}/commit/{sha}",
    }


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, ("channel", "release", "latest")),
        ({"channel": "main"}, ("channel", "main", "main")),
        ({"version": "v1.2.3"}, ("version", "1.2.3", "v1.2.3")),
        ({"version": "1.2.3rc1"}, ("version", "1.2.3rc1", "v1.2.3rc1")),
        ({"ref": "release/candidate-1"}, ("ref", "release/candidate-1", "release/candidate-1")),
    ],
)
def test_update_selectors_are_closed_and_canonical(
    kwargs: dict[str, str], expected: tuple[str, str, str]
) -> None:
    selector = subject.normalize_update_selector(**kwargs)

    assert (selector["kind"], selector["value"], selector["ref"]) == expected


@pytest.mark.parametrize(
    "ref",
    ["../main", "main..old", "refs//heads/main", "main@{1}", "main/", "main\nnext", "-main"],
)
def test_update_refs_reject_revision_and_terminal_injection(ref: str) -> None:
    with pytest.raises(ValueError, match="invalid"):
        subject.normalize_update_selector(ref=ref)


def test_main_check_resolves_one_sha_and_reuses_the_validated_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, float]] = []
    monkeypatch.setattr(subject, "installed_version_snapshot", lambda: _installed())

    def fetch(path: str, timeout: float) -> dict[str, str]:
        calls.append((path, timeout))
        return _commit(_MAIN_SHA)

    first = subject.check_for_update(
        channel="main",
        refresh=True,
        timeout=2,
        home_dir=tmp_path,
        fetch_json=fetch,
        clock=lambda: 1_000,
    )
    second = subject.check_for_update(
        channel="main",
        home_dir=tmp_path,
        fetch_json=lambda *_args: pytest.fail("fresh cache must suppress remote I/O"),
        clock=lambda: 1_001,
    )

    assert calls[0][0] == f"repos/{subject.REPOSITORY}/commits/main?per_page=1"
    assert 0 < calls[0][1] <= 2
    assert first["target"]["commit_sha"] == _MAIN_SHA
    assert first["status"] == "different_target"
    assert first["update_available"] is None
    assert first["cache_hit"] is False
    assert second["target"] == first["target"]
    assert second["cache_hit"] is True


def test_explicit_canonical_prerelease_resolves_its_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(subject, "installed_version_snapshot", lambda: _installed())

    def fetch(path: str, _timeout: float) -> dict[str, str]:
        calls.append(path)
        return _commit(_RELEASE_SHA)

    status = subject.check_for_update(
        version="1.2.3rc1",
        refresh=True,
        home_dir=tmp_path,
        fetch_json=fetch,
        clock=lambda: 1_000,
    )

    assert calls == [f"repos/{subject.REPOSITORY}/commits/v1.2.3rc1?per_page=1"]
    assert status["target"]["version"] == "1.2.3rc1"


def test_exact_commit_resolution_requests_only_one_unused_file_row() -> None:
    calls: list[tuple[str, float]] = []

    def fetch(path: str, timeout: float) -> dict[str, str]:
        calls.append((path, timeout))
        return _commit(_MAIN_SHA)

    resolved = subject._fetch_commit(_MAIN_SHA, 30, fetch)

    assert calls == [(f"repos/{subject.REPOSITORY}/commits/{_MAIN_SHA}?per_page=1", 30)]
    assert resolved == (
        _MAIN_SHA,
        f"https://github.com/{subject.REPOSITORY}/commit/{_MAIN_SHA}",
    )


def test_release_order_places_prereleases_below_their_final() -> None:
    assert subject._release_key("0.2.0a2") < subject._release_key("0.2.0b1")
    assert subject._release_key("0.2.0b2") < subject._release_key("0.2.0rc1")
    assert subject._release_key("0.2.0rc9") < subject._release_key("0.2.0")

    installed = _installed()
    installed["package_version"] = "0.2.0rc1"
    selector = subject.normalize_update_selector(channel="release")
    target = {
        "kind": "release",
        "label": "v0.2.0",
        "version": "0.2.0",
        "ref": "v0.2.0",
        "commit_sha": _RELEASE_SHA,
        "url": f"https://github.com/{subject.REPOSITORY}/releases/tag/v0.2.0",
        "published_at": None,
    }
    assert subject._comparison(installed, selector, target) == ("update_available", True)


def test_release_and_main_workers_merge_cache_entries_without_lost_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    barrier = threading.Barrier(2)
    monkeypatch.setattr(subject, "installed_version_snapshot", lambda: _installed())

    def fetch(path: str, _timeout: float) -> dict[str, object]:
        if path.endswith("/releases/latest"):
            barrier.wait(timeout=5)
            return {
                "draft": False,
                "prerelease": False,
                "tag_name": "v0.2.0",
                "html_url": f"https://github.com/{subject.REPOSITORY}/releases/tag/v0.2.0",
                "published_at": "2026-07-28T00:00:00Z",
            }
        if path.endswith("/commits/main?per_page=1"):
            barrier.wait(timeout=5)
            return _commit(_MAIN_SHA)
        return _commit(_RELEASE_SHA)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                subject.check_for_update,
                channel=channel,
                refresh=True,
                home_dir=tmp_path,
                fetch_json=fetch,
                clock=lambda: 2_000,
            )
            for channel in ("release", "main")
        ]
        results = [future.result(timeout=10) for future in futures]

    cache = subject._read_cache(home_dir=tmp_path)
    assert set(cache["entries"]) == {"channel:release", "channel:main"}
    assert results[0]["target"]["commit_sha"] == _RELEASE_SHA
    assert results[0]["update_available"] is True
    assert results[1]["target"]["commit_sha"] == _MAIN_SHA


def test_cache_projection_rejects_hostile_target_and_nonfinite_timestamps() -> None:
    selector = subject.normalize_update_selector(channel="main")
    entry = {
        "checked_at": float("nan"),
        "expires_at": float("inf"),
        "target": {
            "kind": "main",
            "label": "main\x1b[2J",
            "version": None,
            "ref": "main",
            "commit_sha": _MAIN_SHA,
            "url": f"https://github.com/{subject.REPOSITORY}/commit/{_MAIN_SHA}",
            "published_at": None,
        },
        "error": "bad\x1b[2J",
    }

    status = subject._status_from_entry(
        selector,
        _installed(),
        entry,
        now=3_000,
        cache_hit=True,
    )

    assert status["checked"] is False
    assert status["stale"] is True
    assert status["target"] is None
    assert status["error"] == "cached update target was invalid"


def test_invalid_fresh_cache_entry_is_repaired_without_explicit_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subject, "installed_version_snapshot", lambda: _installed())
    selector = subject.normalize_update_selector(channel="main")
    subject._write_cache(
        {
            "schema_version": subject.CACHE_SCHEMA_VERSION,
            "entries": {
                selector["key"]: {
                    "checked_at": 1_000,
                    "expires_at": 10_000_000,
                    "target": {"kind": "main", "label": "main", "commit_sha": "bad"},
                    "error": "stale cached failure",
                }
            },
        },
        home_dir=tmp_path,
    )
    calls: list[str] = []

    def fetch(path: str, _timeout: float) -> dict[str, str]:
        calls.append(path)
        return _commit(_MAIN_SHA)

    status = subject.check_for_update(
        channel="main",
        home_dir=tmp_path,
        fetch_json=fetch,
        clock=lambda: 1_001,
    )

    assert calls == [f"repos/{subject.REPOSITORY}/commits/main?per_page=1"]
    assert status["target"]["commit_sha"] == _MAIN_SHA
    assert status["cache_hit"] is False


def test_default_cache_reads_the_same_token_fallback_used_for_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary = tmp_path / "unavailable-primary"
    fallback = subject.ensure_private_directory(tmp_path / "token-fallback")
    updates = subject.ensure_private_directory(fallback / "updates")
    monkeypatch.setattr(
        subject,
        "private_runtime_root_candidates",
        lambda: (primary, fallback),
    )
    monkeypatch.setattr(subject, "private_runtime_directory", lambda _name: updates)

    subject._write_cache(
        {
            "schema_version": subject.CACHE_SCHEMA_VERSION,
            "entries": {"channel:main": {"sentinel": True}},
        },
        home_dir=None,
    )

    assert subject._read_cache(home_dir=None)["entries"]["channel:main"]["sentinel"] is True


def test_github_cli_resolution_excludes_the_repository_ancestor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "hostile-repository"
    nested = repository / "work" / "nested"
    (repository / ".git").mkdir(parents=True)
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    captured: dict[str, object] = {}

    def prepare(argv, **kwargs):
        captured["argv"] = list(argv)
        captured["forbidden_roots"] = tuple(kwargs["forbidden_roots"])
        return list(argv)

    monkeypatch.setattr(subject, "prepare_process_argv", prepare)
    monkeypatch.setattr(subject, "freeze_process_argv", lambda argv, **_kwargs: argv)
    monkeypatch.setattr(
        subject,
        "run_bounded_process",
        lambda *_args, **_kwargs: subject.BoundedProcessResult(0, "{}", ""),
    )

    assert subject._gh_api_bytes("repos/example", 1) == b"{}"
    assert repository.resolve() in captured["forbidden_roots"]


def test_pep610_commit_is_not_rebound_to_an_enclosing_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed_sha = "d" * 40

    class FakeDistribution:
        files: tuple[str, ...] = ()

        @staticmethod
        def read_text(name: str) -> str | None:
            assert name == "direct_url.json"
            return json.dumps(
                {
                    "url": subject.REPOSITORY_GIT_URL,
                    "vcs_info": {"vcs": "git", "commit_id": installed_sha},
                }
            )

    monkeypatch.setattr(subject, "distribution", lambda _name: FakeDistribution())
    monkeypatch.setattr(subject, "_find_source_repository", lambda: tmp_path)
    monkeypatch.setattr(
        subject,
        "_git_value",
        lambda *_args: pytest.fail("a non-editable VCS package must keep PEP 610 identity"),
    )

    identity = subject.installed_version_snapshot()

    assert identity["source_revision"] == installed_sha
    assert identity["install_kind"] == "vcs-package"
    assert identity["official_repository"] is True


def test_source_identity_includes_untracked_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        subject,
        "distribution",
        lambda _name: (_ for _ in ()).throw(subject.PackageNotFoundError()),
    )
    monkeypatch.setattr(subject, "_find_source_repository", lambda: tmp_path)

    def run(_repository: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        if arguments[:2] == ["rev-parse", "--verify"]:
            output = "e" * 40
        elif arguments == ["rev-parse", "--abbrev-ref", "HEAD"]:
            output = "main"
        elif arguments == ["remote", "get-url", "origin"]:
            output = subject.REPOSITORY_GIT_URL
        else:
            output = "?? agency_runtime/untracked_runtime.py\n"
        return subprocess.CompletedProcess(["git", *arguments], 0, output, "")

    monkeypatch.setattr(subject, "_run_read_only_git", run)

    identity = subject.installed_version_snapshot()

    assert identity["source_dirty"] is True
    assert ["status", "--porcelain=v1", "--untracked-files=normal"] in calls


def test_source_repository_detection_does_not_walk_out_of_site_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "checkout"
    module = repository / ".venv" / "Lib" / "site-packages" / "agency_runtime" / "core"
    (repository / ".git").mkdir(parents=True)
    module.mkdir(parents=True)
    module_path = module / "update_service.py"
    module_path.write_text("# installed copy\n", encoding="utf-8")
    monkeypatch.setattr(subject, "__file__", str(module_path))

    assert subject._find_source_repository() is None


def test_remote_and_cache_json_reject_duplicate_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    duplicate = b'{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}'
    monkeypatch.setattr(subject, "_gh_api_bytes", lambda *_args: duplicate)
    monkeypatch.setattr(subject, "_https_api_bytes", lambda *_args: duplicate)

    with pytest.raises(subject.UpdateCheckError):
        subject._github_json("repos/example/commits/main", 1)

    path = subject._cache_path(home_dir=tmp_path, create=True)
    path.write_bytes(b'{"schema_version":1,"entries":{},"entries":{"channel:main":{}}}')
    subject.restrict_private_file(path)
    assert subject._read_cache(home_dir=tmp_path)["entries"] == {}


def test_check_timeout_is_one_total_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ticks = iter((10.0, 11.0))
    monkeypatch.setattr(subject, "installed_version_snapshot", lambda: _installed())
    monkeypatch.setattr(subject.time, "monotonic", lambda: next(ticks, 11.0))

    status = subject.check_for_update(
        channel="main",
        refresh=True,
        timeout=0.1,
        home_dir=tmp_path,
        fetch_json=lambda *_args: pytest.fail("expired deadline must suppress I/O"),
        clock=lambda: 4_000,
    )

    assert status["checked"] is True
    assert status["status"] == "unavailable"
    assert status["error"] == "GitHub update check timed out"


def _available_main_status() -> dict[str, Any]:
    selector = subject.normalize_update_selector(channel="main")
    target = {
        "kind": "main",
        "label": "main",
        "version": None,
        "ref": "main",
        "commit_sha": _MAIN_SHA,
        "url": f"https://github.com/{subject.REPOSITORY}/commit/{_MAIN_SHA}",
        "published_at": None,
    }
    return subject._status_from_entry(
        selector,
        _installed(),
        {"checked_at": 5_000, "expires_at": 6_000, "target": target, "error": None},
        now=5_000,
        cache_hit=False,
    )


def test_attended_plan_pins_the_resolved_sha_and_never_executes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    interpreter = str(Path("C:/owner tools/python.exe"))
    monkeypatch.setattr(
        subject,
        "_attended_upgrade_install",
        lambda source: (
            [
                interpreter,
                "-I",
                "-m",
                "pip",
                "--isolated",
                "--disable-pip-version-check",
                "install",
                "--upgrade",
                "--force-reinstall",
                source,
            ],
            "pip",
            interpreter,
        ),
    )

    plan = subject.attended_upgrade_plan(_available_main_status())

    assert plan["mode"] == "attended-external"
    assert plan["installer"] == "pip"
    assert plan["mutation_performed"] is False
    assert plan["requires_owner_execution"] is True
    assert plan["commands"][0]["argv"][:4] == [interpreter, "-I", "-m", "pip"]
    assert f"@{_MAIN_SHA}" in plan["commands"][0]["display"]
    assert "@main" not in plan["commands"][0]["display"]
    assert plan["commands"][1]["argv"][:4] == [
        interpreter,
        "-I",
        "-m",
        "agency_runtime.cli",
    ]
    assert plan["commands"][1]["argv"][-3:] == ["--agent", "codex", "--no-dashboard"]


def _prepared_interpreter(path: Path) -> subject.PreparedProcessArgv:
    return subject.PreparedProcessArgv([str(path)], artifact_paths=(str(path),))


def test_windows_upgrade_display_is_an_inert_powershell_invocation() -> None:
    display = subject._display_argv(
        [r"C:\Owner O'Brien & Co\uv.exe", "tool", "$(host); (unsafe)"],
        platform_name="nt",
    )

    assert display == ("& 'C:\\Owner O''Brien & Co\\uv.exe' 'tool' '$(host); (unsafe)'")


def test_upgrade_interpreter_rejects_a_repository_contained_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    prefix = repository / ".venv"
    executable = prefix / ("python.exe" if os.name == "nt" else "python")
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"python")
    (repository / ".git").mkdir()
    monkeypatch.setattr(subject.sys, "prefix", str(prefix))
    monkeypatch.setattr(subject.sys, "executable", str(executable))
    monkeypatch.setattr(subject, "validate_private_directory", lambda path: path.resolve())
    monkeypatch.setattr(subject, "_upgrade_repository_roots", lambda: (repository,))
    monkeypatch.setattr(
        subject,
        "distribution",
        lambda _name: pytest.fail("repository environments must be rejected before metadata"),
    )

    with pytest.raises(PermissionError, match="inside a repository"):
        subject._prepared_upgrade_interpreter()


def test_uv_resolution_excludes_nested_repository_without_excluding_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "owner home"
    prefix = home / "uv" / "tools" / "agency-runtime"
    repository = home / "work" / "repository"
    binary_directory = home / ".local" / "bin"
    prefix.mkdir(parents=True)
    (repository / ".git").mkdir(parents=True)
    binary_directory.mkdir(parents=True)
    executable = binary_directory / ("uv.exe" if os.name == "nt" else "uv")
    executable.write_bytes(b"uv")
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(binary_directory))

    prepared = subject._prepared_uv_launcher(
        prefix=prefix,
        forbidden_roots=(repository,),
    )

    assert prepared is not None
    assert Path(prepared[0]).resolve() == executable.resolve()


def test_uv_resolution_rejects_a_nested_repository_from_a_broad_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "owner-home"
    prefix = home / "uv" / "tools" / "agency-runtime"
    repository = home / "work" / "evil-repository"
    binary_directory = repository / "bin"
    prefix.mkdir(parents=True)
    (repository / ".git").mkdir(parents=True)
    binary_directory.mkdir()
    executable = binary_directory / ("uv.exe" if os.name == "nt" else "uv")
    executable.write_bytes(b"uv")
    executable.chmod(0o700)
    monkeypatch.chdir(home)
    monkeypatch.setenv("PATH", str(binary_directory))

    assert subject._prepared_uv_launcher(prefix=prefix, forbidden_roots=()) is None


def test_uv_resolution_fails_closed_when_preparation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "prepare_process_argv",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unsafe uv")),
    )

    assert subject._prepared_uv_launcher(prefix=tmp_path, forbidden_roots=()) is None


def test_attended_install_prefers_validated_uv_tool_even_when_pip_is_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = tmp_path / "tool-environment"
    prefix.mkdir()
    (prefix / "uv-receipt.toml").write_text("receipt", encoding="utf-8")
    interpreter = _prepared_interpreter(prefix / "python.exe")
    uv_executable = str(tmp_path / "owner tools" / "uv.exe")
    uv_launcher = _prepared_interpreter(Path(uv_executable))
    monkeypatch.setattr(
        subject,
        "_prepared_upgrade_interpreter",
        lambda: (interpreter, prefix, ()),
    )
    monkeypatch.setattr(
        subject,
        "_validated_agency_uv_tool_environment",
        lambda **_kwargs: tmp_path / "bin" / "agency.exe",
    )
    monkeypatch.setattr(subject, "_prepared_uv_launcher", lambda **_kwargs: uv_launcher)
    monkeypatch.setattr(
        subject,
        "_uv_tool_targets_current_environment",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        subject,
        "_pip_module_available",
        lambda *_args, **_kwargs: pytest.fail("a uv-owned environment must not use pip"),
    )

    selected = subject._attended_upgrade_install("agency-runtime @ git+https://safe.test@abc")

    assert selected is not None
    command, installer, refresh_interpreter = selected
    assert installer == "uv-tool"
    assert refresh_interpreter == interpreter[0]
    assert command[:7] == [
        uv_executable,
        "tool",
        "install",
        "--force",
        "--refresh",
        "--no-config",
        "agency-runtime @ git+https://safe.test@abc",
    ]
    assert "pip" not in command


def test_uv_target_probe_binds_tool_and_binary_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool_directory = tmp_path / "tools"
    prefix = tool_directory / "agency-runtime"
    binary_directory = tmp_path / "bin"
    prefix.mkdir(parents=True)
    binary_directory.mkdir()
    entrypoint = binary_directory / ("agency.exe" if os.name == "nt" else "agency")
    entrypoint.write_bytes(b"agency")
    launcher = _prepared_interpreter(tmp_path / ("uv.exe" if os.name == "nt" else "uv"))
    for key in subject.UV_TARGET_OVERRIDE_KEYS:
        monkeypatch.delenv(key, raising=False)

    def run(argv, **_kwargs):
        value = binary_directory if "--bin" in argv else tool_directory
        return subject.BoundedProcessResult(0, f"{value}\n", "")

    monkeypatch.setattr(subject, "run_bounded_process", run)

    assert subject._uv_tool_targets_current_environment(
        launcher,
        prefix=prefix,
        entrypoint=entrypoint,
    )


@pytest.mark.parametrize("override", sorted(subject.UV_TARGET_OVERRIDE_KEYS))
def test_uv_target_probe_rejects_environment_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    override: str,
) -> None:
    prefix = tmp_path / "tools" / "agency-runtime"
    prefix.mkdir(parents=True)
    entrypoint = tmp_path / "bin" / "agency"
    entrypoint.parent.mkdir()
    entrypoint.write_bytes(b"agency")
    launcher = _prepared_interpreter(tmp_path / ("uv.exe" if os.name == "nt" else "uv"))
    for key in subject.UV_TARGET_OVERRIDE_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(override, str(tmp_path / "redirected"))
    monkeypatch.setattr(
        subject,
        "_bounded_uv_directory",
        lambda *_args, **_kwargs: pytest.fail("overrides must fail before probing uv"),
    )

    assert not subject._uv_tool_targets_current_environment(
        launcher,
        prefix=prefix,
        entrypoint=entrypoint,
    )


def test_uv_target_probe_rejects_a_different_tool_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = tmp_path / "expected"
    prefix = expected / "agency-runtime"
    actual = tmp_path / "other-tools"
    binary_directory = tmp_path / "bin"
    for directory in (prefix, actual, binary_directory):
        directory.mkdir(parents=True)
    entrypoint = binary_directory / "agency"
    entrypoint.write_bytes(b"agency")
    launcher = _prepared_interpreter(tmp_path / ("uv.exe" if os.name == "nt" else "uv"))
    for key in subject.UV_TARGET_OVERRIDE_KEYS:
        monkeypatch.delenv(key, raising=False)

    def run(argv, **_kwargs):
        value = binary_directory if "--bin" in argv else actual
        return subject.BoundedProcessResult(0, f"{value}\n", "")

    monkeypatch.setattr(subject, "run_bounded_process", run)

    assert not subject._uv_tool_targets_current_environment(
        launcher,
        prefix=prefix,
        entrypoint=entrypoint,
    )


def test_uv_target_probe_rejects_a_renamed_agency_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool_directory = tmp_path / "tools"
    prefix = tool_directory / "renamed-environment"
    binary_directory = tmp_path / "bin"
    prefix.mkdir(parents=True)
    binary_directory.mkdir()
    entrypoint = binary_directory / ("agency.exe" if os.name == "nt" else "agency")
    entrypoint.write_bytes(b"agency")
    launcher = _prepared_interpreter(tmp_path / ("uv.exe" if os.name == "nt" else "uv"))
    for key in subject.UV_TARGET_OVERRIDE_KEYS:
        monkeypatch.delenv(key, raising=False)

    def run(argv, **_kwargs):
        value = binary_directory if "--bin" in argv else tool_directory
        return subject.BoundedProcessResult(0, f"{value}\n", "")

    monkeypatch.setattr(subject, "run_bounded_process", run)

    assert not subject._uv_tool_targets_current_environment(
        launcher,
        prefix=prefix,
        entrypoint=entrypoint,
    )


def test_attended_plan_fails_closed_without_pip_or_validated_uv_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = tmp_path / "environment"
    prefix.mkdir()
    interpreter = _prepared_interpreter(prefix / "python.exe")
    monkeypatch.setattr(
        subject,
        "_prepared_upgrade_interpreter",
        lambda: (interpreter, prefix, ()),
    )
    monkeypatch.setattr(subject, "_pip_module_available", lambda *_args, **_kwargs: False)

    plan = subject.attended_upgrade_plan(_available_main_status())

    assert plan["mode"] == "unavailable"
    assert plan["mutation_performed"] is False
    assert plan["commands"] == []
    assert "no usable pip module" in plan["reason"]


def test_attended_install_uses_isolated_pip_only_without_a_uv_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = tmp_path / "environment"
    prefix.mkdir()
    interpreter = _prepared_interpreter(prefix / ("python.exe" if os.name == "nt" else "python"))
    monkeypatch.setattr(
        subject,
        "_prepared_upgrade_interpreter",
        lambda: (interpreter, prefix, ()),
    )
    monkeypatch.setattr(subject, "_pip_module_available", lambda *_args, **_kwargs: True)

    selected = subject._attended_upgrade_install("agency-runtime @ git+https://safe.test@abc")

    assert selected is not None
    command, installer, refresh_interpreter = selected
    assert installer == "pip"
    assert refresh_interpreter == interpreter[0]
    assert command == [
        interpreter[0],
        "-I",
        "-m",
        "pip",
        "--isolated",
        "--disable-pip-version-check",
        "install",
        "--upgrade",
        "--force-reinstall",
        "agency-runtime @ git+https://safe.test@abc",
    ]


def test_uv_tool_environment_requires_exact_bounded_agency_receipt(
    tmp_path: Path,
) -> None:
    receipt = tmp_path / "uv-receipt.toml"
    entrypoint = tmp_path / "bin" / ("agency.exe" if os.name == "nt" else "agency")
    entrypoint.parent.mkdir()
    entrypoint.write_bytes(b"launcher")
    entrypoint.chmod(0o700)
    receipt.write_text(
        "[tool]\n"
        'requirements = [{ name = "agency-runtime", git = "https://example.test/repo" }]\n'
        "entrypoints = [\n"
        f'    {{ name = "agency", install-path = "{entrypoint.as_posix()}", '
        'from = "agency-runtime" },\n'
        "]\n",
        encoding="utf-8",
    )

    assert (
        subject._validated_agency_uv_tool_environment(prefix=tmp_path, forbidden_roots=())
        == entrypoint
    )

    receipt.write_text(
        "[unrelated]\n"
        'requirements = [{ name = "agency-runtime", version = "1.0" }]\n'
        "[tool]\n"
        'requirements = [{ name = "unrelated", version = "1.0" }]\n'
        "entrypoints = [\n"
        f'    {{ name = "agency", install-path = "{entrypoint.as_posix()}", '
        'from = "agency-runtime" },\n'
        "]\n",
        encoding="utf-8",
    )
    assert not subject._validated_agency_uv_tool_environment(
        prefix=tmp_path,
        forbidden_roots=(),
    )


def test_uv_tool_environment_rejects_a_different_entrypoint_name(tmp_path: Path) -> None:
    entrypoint = tmp_path / "bin" / ("other.exe" if os.name == "nt" else "other")
    entrypoint.parent.mkdir()
    entrypoint.write_bytes(b"launcher")
    entrypoint.chmod(0o700)
    (tmp_path / "uv-receipt.toml").write_text(
        "[tool]\n"
        'requirements = [{ name = "agency-runtime", version = "1.0" }]\n'
        "entrypoints = [\n"
        f'    {{ name = "agency", install-path = "{entrypoint.as_posix()}", '
        'from = "agency-runtime" },\n'
        "]\n",
        encoding="utf-8",
    )

    assert (
        subject._validated_agency_uv_tool_environment(prefix=tmp_path, forbidden_roots=()) is None
    )


@pytest.mark.parametrize(
    "payload",
    [
        b"\xff\xfe",
        b"[tool]\rrequirements = []\nentrypoints = []\n",
        b"[tool]\nrequirements = []\nentrypoints = []\n[tool]\n",
        (
            b'[tool]\nrequirements = [{ name = "agency-runtime", name = "other" }]\n'
            b"entrypoints = []\n"
        ),
    ],
)
def test_uv_tool_environment_rejects_ambiguous_receipts(
    tmp_path: Path,
    payload: bytes,
) -> None:
    (tmp_path / "uv-receipt.toml").write_bytes(payload)

    assert not subject._validated_agency_uv_tool_environment(
        prefix=tmp_path,
        forbidden_roots=(),
    )


def test_uv_tool_environment_rejects_missing_and_oversized_receipts(tmp_path: Path) -> None:
    assert not subject._validated_agency_uv_tool_environment(
        prefix=tmp_path,
        forbidden_roots=(),
    )

    (tmp_path / "uv-receipt.toml").write_bytes(b"x" * (subject.UV_RECEIPT_MAX_BYTES + 1))
    assert not subject._validated_agency_uv_tool_environment(
        prefix=tmp_path,
        forbidden_roots=(),
    )


@pytest.mark.skipif(os.name == "nt", reason="uv uses copied launchers on Windows")
def test_uv_tool_environment_accepts_only_an_in_prefix_posix_symlink(
    tmp_path: Path,
) -> None:
    prefix = tmp_path / "tools" / "agency-runtime"
    target = prefix / "bin" / "agency"
    entrypoint = tmp_path / "bin" / "agency"
    target.parent.mkdir(parents=True)
    entrypoint.parent.mkdir()
    target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    target.chmod(0o700)
    entrypoint.symlink_to(target)
    (prefix / "uv-receipt.toml").write_text(
        "[tool]\n"
        'requirements = [{ name = "agency-runtime", version = "1.0" }]\n'
        "entrypoints = [\n"
        f'    {{ name = "agency", install-path = "{entrypoint}", '
        'from = "agency-runtime" },\n'
        "]\n",
        encoding="utf-8",
    )

    assert (
        subject._validated_agency_uv_tool_environment(prefix=prefix, forbidden_roots=())
        == entrypoint
    )

    outside = tmp_path / "outside" / "agency"
    outside.parent.mkdir()
    outside.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    outside.chmod(0o700)
    entrypoint.unlink()
    entrypoint.symlink_to(outside)
    assert subject._validated_agency_uv_tool_environment(prefix=prefix, forbidden_roots=()) is None


def test_pip_capability_requires_regular_entrypoint_inside_exact_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = tmp_path / "environment"
    package_root = prefix / "Lib" / "site-packages"
    pip_root = package_root / "pip"
    pip_root.mkdir(parents=True)
    (pip_root / "__main__.py").write_text("raise SystemExit(0)\n", encoding="utf-8")

    class PipDistribution:
        def __init__(self) -> None:
            self.metadata = {"Name": "pip"}

        @staticmethod
        def locate_file(_name: str) -> Path:
            return package_root

    monkeypatch.setattr(subject, "distribution", lambda _name: PipDistribution())
    monkeypatch.setattr(
        subject,
        "run_bounded_process",
        lambda *_args, **_kwargs: subject.BoundedProcessResult(0, "pip 1", ""),
    )
    interpreter = _prepared_interpreter(prefix / "python.exe")
    assert subject._pip_module_available(interpreter, prefix=prefix) is True

    outside = tmp_path / "outside"
    (outside / "pip").mkdir(parents=True)
    (outside / "pip" / "__main__.py").write_text("raise SystemExit(0)\n", encoding="utf-8")

    class OutsideDistribution(PipDistribution):
        @staticmethod
        def locate_file(_name: str) -> Path:
            return outside

    monkeypatch.setattr(subject, "distribution", lambda _name: OutsideDistribution())
    assert subject._pip_module_available(interpreter, prefix=prefix) is False


@pytest.mark.parametrize(
    "result",
    [
        subject.BoundedProcessResult(1, "", "broken"),
        subject.BoundedProcessResult(0, "", "", timed_out=True),
        subject.BoundedProcessResult(0, "pip", "", stdout_truncated=True),
        subject.BoundedProcessResult(0, "pip", "", stderr_truncated=True),
    ],
)
def test_pip_capability_requires_a_complete_successful_isolated_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    result: subject.BoundedProcessResult,
) -> None:
    package_root = tmp_path / "Lib" / "site-packages"
    (package_root / "pip").mkdir(parents=True)
    (package_root / "pip" / "__main__.py").write_text("pass\n", encoding="utf-8")

    class PipDistribution:
        def __init__(self) -> None:
            self.metadata = {"Name": "pip"}

        @staticmethod
        def locate_file(_name: str) -> Path:
            return package_root

    captured: dict[str, object] = {}

    def run(argv, **kwargs):
        captured["argv"] = list(argv)
        captured.update(kwargs)
        return result

    monkeypatch.setattr(subject, "distribution", lambda _name: PipDistribution())
    monkeypatch.setattr(subject, "run_bounded_process", run)
    interpreter = _prepared_interpreter(tmp_path / "python.exe")

    assert not subject._pip_module_available(interpreter, prefix=tmp_path)
    assert captured["argv"][-6:] == [
        "-I",
        "-m",
        "pip",
        "--isolated",
        "--disable-pip-version-check",
        "--version",
    ]
    assert captured["cwd"] == str(tmp_path)
    assert "PYTHONPATH" not in captured["env"]


def test_cached_notice_validates_untrusted_label_before_terminal_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subject, "installed_version_snapshot", lambda: _installed())
    subject.check_for_update(
        channel="release",
        refresh=True,
        home_dir=tmp_path,
        fetch_json=lambda path, _timeout: (
            {
                "draft": False,
                "prerelease": False,
                "tag_name": "v0.2.0",
                "html_url": f"https://github.com/{subject.REPOSITORY}/releases/tag/v0.2.0",
                "published_at": "2026-07-28T00:00:00Z",
            }
            if path.endswith("/releases/latest")
            else _commit(_RELEASE_SHA)
        ),
        clock=lambda: 7_000,
    )
    assert "release" in str(subject.cached_startup_notice(home_dir=tmp_path, clock=lambda: 7_001))

    cache = subject._read_cache(home_dir=tmp_path)
    cache["entries"]["channel:release"]["target"]["label"] = "v0.2.0\x1b[2J"
    subject._write_cache(cache, home_dir=tmp_path)

    assert subject.cached_startup_notice(home_dir=tmp_path, clock=lambda: 7_001) is None


def test_dashboard_snapshot_reuses_identity_and_keeps_stale_refresh_visible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def identity() -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return _installed()

    monkeypatch.setattr(subject, "installed_version_snapshot", identity)
    monkeypatch.setattr(subject, "_DASHBOARD_IDENTITY_CACHE", None)
    monkeypatch.setattr(subject, "_schedule_selector", lambda *_args: False)

    first = subject.dashboard_update_snapshot(home_dir=tmp_path, schedule=True)
    second = subject.dashboard_update_snapshot(home_dir=tmp_path, schedule=True)

    assert calls == 1
    assert first["checking"] is True
    assert second["checking"] is True
    assert first["release"]["checking"] is True
    assert first["main"]["checking"] is True


def test_git_hub_cli_environment_does_not_forward_unrelated_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENCY_PRIVATE_SENTINEL", "must-not-cross-process-boundary")
    monkeypatch.setenv("GH_ENTERPRISE_TOKEN", "wrong-host-secret")
    monkeypatch.setenv("GH_TOKEN", "test-token")

    environment = subject._gh_environment()

    assert environment["GH_TOKEN"] == "test-token"
    assert "GH_ENTERPRISE_TOKEN" not in environment
    assert "AGENCY_PRIVATE_SENTINEL" not in environment
    assert environment["GH_PROMPT_DISABLED"] == "1"


def test_vcs_distribution_identity_preserves_the_pinned_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Distribution:
        files: tuple[object, ...] = ()

        @staticmethod
        def read_text(name: str) -> str | None:
            if name != "direct_url.json":
                return None
            return json.dumps(
                {
                    "url": subject.REPOSITORY_GIT_URL,
                    "vcs_info": {"vcs": "git", "commit_id": _MAIN_SHA},
                }
            )

    monkeypatch.setattr(subject, "distribution", lambda _name: Distribution())
    monkeypatch.setattr(subject, "_find_source_repository", lambda: None)

    identity = subject.installed_version_snapshot()

    assert identity["install_kind"] == "vcs-package"
    assert identity["source_revision"] == _MAIN_SHA
    assert identity["official_repository"] is True
    assert identity["build_identity"].endswith(_MAIN_SHA[:12])
