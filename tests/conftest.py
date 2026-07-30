"""Suite-wide isolation that preserves the production storage trust boundary."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import suppress
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.private_paths import (
    PrivateDirectoryIdentity,
    allocate_host_private_directory,
    allocate_private_directory,
    private_runtime_directory,
    remove_private_directory,
)
from tests.runtime_support import trusted_test_interpreter

_WINDOWS_TEMP_ANCHOR_ATTRIBUTE = "_agency_runtime_windows_temp_anchor"
_WINDOWS_ORIGINAL_TEMPDIR_ATTRIBUTE = "_agency_runtime_windows_original_tempdir"
_WINDOWS_PYTEST_PATHLIB_MKDIR_ATTRIBUTE = "_agency_runtime_pytest_pathlib_mkdir"
_WINDOWS_PYTEST_TMPDIR_MKDIR_ATTRIBUTE = "_agency_runtime_pytest_tmpdir_mkdir"
_WINDOWS_OS_MKDIR_ATTRIBUTE = "_agency_runtime_os_mkdir"
_RUNTIME_CONFIGURATION_IDENTITY_MARKER = "runtime_configuration_identity"
_OFFLINE_CONFIGURATION = (
    "providers: []\n"
    "judge:\n"
    '  model: ""\n'
    '  base_url: ""\n'
    '  api_key: ""\n'
    '  api_key_env: ""\n'
    "  ollama_mode: false\n"
    "ollama:\n"
    "  enabled: false\n"
)


class _OSFacade:
    """Delegate to the real OS module while keeping test overrides local."""

    def __init__(
        self,
        real_os: Any,
        *,
        missing: frozenset[str] = frozenset(),
        **overrides: Any,
    ) -> None:
        self._real_os = real_os
        self._missing = missing
        self._overrides = overrides

    def __getattr__(self, name: str) -> Any:
        if name in self._missing:
            raise AttributeError(name)
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._real_os, name)


@pytest.fixture
def os_facade() -> type[_OSFacade]:
    """Return the process-safe OS facade used by platform simulation tests."""

    return _OSFacade


def _test_runtime_root(session_root: Path, node_id: str) -> Path:
    """Return a bounded unique path without creating one directory per test."""

    digest = sha256(node_id.encode("utf-8")).hexdigest()
    return session_root / "items" / digest


def _write_offline_configuration(config_path: Path, store_path: Path) -> None:
    """Write the quota-free test configuration at one already-private path."""

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        f'store:\n  db_path: "{store_path.as_posix()}"\n{_OFFLINE_CONFIGURATION}',
        encoding="utf-8",
    )


@pytest.fixture(scope="session")
def _runtime_isolation_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Allocate one private process root for lazy per-test isolation paths."""

    return tmp_path_factory.mktemp("runtime-isolation")


@pytest.fixture(scope="session")
def _shared_offline_configuration(_runtime_isolation_root: Path) -> Path:
    """Materialize the ordinary offline configuration once per pytest process."""

    config_path = _runtime_isolation_root / "offline-config" / "agency.yaml"
    # The ordinary fixture always supplies a unique AGENCY_DB_PATH. Point the
    # file-level fallback at an existing directory so an unmarked test that
    # removes the override cannot silently share mutable Store state.
    _write_offline_configuration(
        config_path,
        config_path.parent,
    )
    return config_path


@pytest.fixture(autouse=True)
def _isolate_runtime_master_state(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    _runtime_isolation_root: Path,
) -> Iterator[None]:
    """Exercise the real fail-enabled reader against per-test durable state."""

    from agency_runtime.core import runtime_control

    original_path = runtime_control.runtime_control_path
    runtime_root = _test_runtime_root(_runtime_isolation_root, request.node.nodeid)
    isolated = runtime_root / "runtime-control" / "control.json"

    def isolated_control_path(
        *,
        home_dir: str | Path | None = None,
    ) -> Path:
        if home_dir is not None:
            return original_path(home_dir=home_dir)
        return isolated

    runtime_control.clear_runtime_control_cache()
    monkeypatch.setattr(runtime_control, "runtime_control_path", isolated_control_path)
    yield
    runtime_control.clear_runtime_control_cache()


@pytest.fixture(autouse=True)
def _isolate_runtime_configuration(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Prevent ordinary tests from inheriting live operator inference settings.

    Provider integration tests opt in by writing an explicit configuration or
    monkeypatching the transport. The suite-wide baseline is deliberately
    offline so a local regression run cannot spend provider quota, depend on a
    workstation's OAuth state, or change behavior with the user's config.

    Ordinary tests reuse one immutable config and receive only a unique lazy
    database path. Tests that exercise configuration or environment identity
    opt out with ``runtime_configuration_identity`` and retain the historical
    per-test config file with no database environment override.
    """

    from agency_runtime.core.config import reset_config_cache
    from agency_runtime.core.workforce.cache import clear_workforce_caches

    identity_test = request.node.get_closest_marker(_RUNTIME_CONFIGURATION_IDENTITY_MARKER)
    if identity_test is not None:
        tmp_path = request.getfixturevalue("tmp_path")
        runtime_root = tmp_path.parent / f".{tmp_path.name}-agency-runtime"
        config_path = runtime_root / "offline-runtime" / "agency.yaml"
        store_path = runtime_root / "offline-runtime" / "agency.db"
        _write_offline_configuration(config_path, store_path)
    else:
        isolation_root = request.getfixturevalue("_runtime_isolation_root")
        config_path = request.getfixturevalue("_shared_offline_configuration")
        runtime_root = _test_runtime_root(isolation_root, request.node.nodeid)
        store_path = runtime_root / "offline-runtime" / "agency.db"
    for name in (
        "AGENCY_JUDGE_API_KEY",
        "AGENCY_JUDGE_BASE_URL",
        "AGENCY_JUDGE_MODEL",
        "LITELLM_API_KEY",
        "OLLAMA_BASE_URL",
        "AGENCY_OLLAMA_FALLBACK_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    if identity_test is not None:
        monkeypatch.delenv("AGENCY_DB_PATH", raising=False)
    else:
        monkeypatch.setenv("AGENCY_DB_PATH", str(store_path))
    reset_config_cache()
    clear_workforce_caches()
    yield
    clear_workforce_caches()
    reset_config_cache()


@pytest.fixture
def git_integration_root(tmp_path: Path) -> Iterator[Path]:
    """Keep real Windows Git worktree tests below its hard path boundary."""

    path_probe = tmp_path / "repository" / ".git" / "worktrees" / f"w-{'0' * 24}"
    if os.name != "nt" or len(str(path_probe)) < 220:
        yield tmp_path
        return

    try:
        identity = allocate_host_private_directory(prefix="git-tests")
    except (OSError, PermissionError, RuntimeError):
        pytest.skip("Windows Git integration requires a short host-attested test root")
    short_probe = identity.path / "repository" / ".git" / "worktrees" / f"w-{'0' * 24}"
    try:
        if len(str(short_probe)) >= 220:
            pytest.skip("host-attested Windows Git test root is still too long")
        yield identity.path
    finally:
        remove_private_directory(identity)


@pytest.fixture(scope="session")
def private_installer_launcher_files(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, Path]:
    """Build one importable package copy below a private test namespace."""

    import yaml

    from agency_runtime.core import process_argv

    runtime = tmp_path_factory.mktemp("private-installer-runtime")
    source_package = Path(process_argv.agency_bootstrap_path()).parent
    package = runtime / "agency_runtime"
    shutil.copytree(
        source_package,
        package,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    shutil.copytree(
        Path(yaml.__file__).parent,
        runtime / "yaml",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    executable = trusted_test_interpreter()
    bootstrap = package / "_bootstrap.py"
    package.chmod(0o700)
    bootstrap.chmod(0o700)
    return executable, bootstrap


@pytest.fixture
def private_installer_launcher(
    monkeypatch: pytest.MonkeyPatch,
    private_installer_launcher_files: tuple[Path, Path],
) -> tuple[Path, Path]:
    """Bind installer generation to the private importable launcher copy."""

    from agency_runtime.core import installer, installer_orchestration, installer_payloads

    executable, bootstrap = private_installer_launcher_files

    def launcher_paths() -> tuple[str, str]:
        return str(executable), str(bootstrap)

    monkeypatch.setattr(installer_payloads, "launcher_artifact_paths", launcher_paths)
    monkeypatch.setattr(installer, "_launcher_artifact_paths", launcher_paths)
    monkeypatch.setattr(
        installer_orchestration,
        "_prepare_adapter_launcher_paths",
        launcher_paths,
    )
    return executable, bootstrap


def _pytest_private_root() -> tuple[Path, PrivateDirectoryIdentity | None]:
    """Use product state normally or one exact host-attested scratch identity."""

    try:
        primary = private_runtime_directory("test-runs")
        probe = allocate_private_directory(primary, prefix="pytest-probe")
        remove_private_directory(probe)
        return primary, None
    except (OSError, PermissionError):
        identity = allocate_host_private_directory(prefix="pytest-cache")
        return identity.path, identity


def pytest_configure(config: pytest.Config) -> None:
    """Put implicit Windows pytest storage below a private user-owned anchor."""

    if os.name != "nt":
        return
    temp_root, identity = _pytest_private_root()
    if identity is None:
        identity = allocate_private_directory(temp_root, prefix="pytest-cache")
    from _pytest import pathlib as pytest_pathlib
    from _pytest import tmpdir as pytest_tmpdir
    from _pytest.cacheprovider import Cache

    original_pathlib_mkdir = pytest_pathlib.make_numbered_dir
    original_tmpdir_mkdir = pytest_tmpdir.make_numbered_dir
    original_os_mkdir = os.mkdir

    def restricted_safe_numbered_dir(root: Path, prefix: str, mode: int = 0o700) -> Path:
        del mode
        return original_pathlib_mkdir(root, prefix, 0o777)

    pytest_pathlib.make_numbered_dir = restricted_safe_numbered_dir
    pytest_tmpdir.make_numbered_dir = restricted_safe_numbered_dir

    def restricted_safe_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        try:
            Path(path).absolute().relative_to(temp_root)
        except (TypeError, ValueError):
            pass
        else:
            mode = 0o777
        if dir_fd is None:
            original_os_mkdir(path, mode)
        else:
            original_os_mkdir(path, mode, dir_fd=dir_fd)

    os.mkdir = restricted_safe_mkdir
    user_root = temp_root / f"pytest-of-{pytest_tmpdir.get_user() or 'unknown'}"
    user_root.mkdir(exist_ok=True)
    cache_root = identity.path
    config._inicache["cache_dir"] = str(cache_root)
    config.cache = Cache(cache_root, config, _ispytest=True)
    setattr(config, _WINDOWS_TEMP_ANCHOR_ATTRIBUTE, identity)
    setattr(config, _WINDOWS_ORIGINAL_TEMPDIR_ATTRIBUTE, tempfile.tempdir)
    setattr(config, _WINDOWS_PYTEST_PATHLIB_MKDIR_ATTRIBUTE, original_pathlib_mkdir)
    setattr(config, _WINDOWS_PYTEST_TMPDIR_MKDIR_ATTRIBUTE, original_tmpdir_mkdir)
    setattr(config, _WINDOWS_OS_MKDIR_ATTRIBUTE, original_os_mkdir)
    tempfile.tempdir = str(temp_root)
    assert user_root.is_dir()


def pytest_unconfigure(config: pytest.Config) -> None:
    """Remove only the exact private anchor created by this pytest process."""

    identity = getattr(config, _WINDOWS_TEMP_ANCHOR_ATTRIBUTE, None)
    if not isinstance(identity, PrivateDirectoryIdentity):
        return
    from _pytest import pathlib as pytest_pathlib
    from _pytest import tmpdir as pytest_tmpdir

    original_pathlib_mkdir = getattr(
        config,
        _WINDOWS_PYTEST_PATHLIB_MKDIR_ATTRIBUTE,
        None,
    )
    original_tmpdir_mkdir = getattr(
        config,
        _WINDOWS_PYTEST_TMPDIR_MKDIR_ATTRIBUTE,
        None,
    )
    original_os_mkdir = getattr(config, _WINDOWS_OS_MKDIR_ATTRIBUTE, None)
    if original_pathlib_mkdir is not None:
        pytest_pathlib.make_numbered_dir = original_pathlib_mkdir
    if original_tmpdir_mkdir is not None:
        pytest_tmpdir.make_numbered_dir = original_tmpdir_mkdir
    if original_os_mkdir is not None:
        os.mkdir = original_os_mkdir
    tempfile.tempdir = getattr(config, _WINDOWS_ORIGINAL_TEMPDIR_ATTRIBUTE, None)
    with suppress(OSError, PermissionError):
        remove_private_directory(identity)
