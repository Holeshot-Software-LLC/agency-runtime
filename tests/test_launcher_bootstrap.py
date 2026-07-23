from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import agency_runtime._bootstrap as isolated_bootstrap
from agency_runtime.core import launcher_bootstrap
from agency_runtime.core.private_paths import PrivateDirectoryIdentity
from agency_runtime.core.process_argv import agency_bootstrap_path


def _snapshot(path: str | Path) -> SimpleNamespace:
    target = Path(path)
    payload = target.read_bytes()
    return SimpleNamespace(
        lexical_path=str(target.resolve()),
        lexical_size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def _private_staging(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    *,
    minimal_runtime: bool = True,
) -> None:
    root.mkdir()
    counter = 0

    def allocate(parent: Path, *, prefix: str) -> PrivateDirectoryIdentity:
        nonlocal counter
        counter += 1
        target = parent / f"{prefix}-{counter}"
        target.mkdir()
        status = target.stat()
        return PrivateDirectoryIdentity(target, int(status.st_dev), int(status.st_ino))

    def remove(identity: PrivateDirectoryIdentity) -> None:
        if identity.path.exists():
            shutil.rmtree(identity.path)

    monkeypatch.setattr(launcher_bootstrap, "private_runtime_directory", lambda _name: root)
    monkeypatch.setattr(launcher_bootstrap, "allocate_private_directory", allocate)
    monkeypatch.setattr(launcher_bootstrap, "remove_private_directory", remove)
    monkeypatch.setattr(launcher_bootstrap, "restrict_private_directory", lambda _path: None)
    monkeypatch.setattr(launcher_bootstrap, "restrict_private_file", lambda _path: None)
    monkeypatch.setattr(launcher_bootstrap.os, "fsync", lambda _descriptor: None)
    monkeypatch.setattr(
        launcher_bootstrap,
        "validate_private_directory",
        lambda path: Path(path),
    )
    monkeypatch.setattr(launcher_bootstrap, "snapshot_persistent_artifact", _snapshot)
    if minimal_runtime:
        bootstrap_payload = Path(agency_bootstrap_path()).read_bytes()
        yaml_payload = b"# projected dependency fixture\n"
        monkeypatch.setattr(
            launcher_bootstrap,
            "_collect_runtime_files",
            lambda _source: (
                launcher_bootstrap._RuntimeFile(
                    "agency_runtime/_bootstrap.py",
                    bootstrap_payload,
                    hashlib.sha256(bootstrap_payload).hexdigest(),
                ),
                launcher_bootstrap._RuntimeFile(
                    "yaml/__init__.py",
                    yaml_payload,
                    hashlib.sha256(yaml_payload).hexdigest(),
                ),
            ),
        )


def test_private_runtime_is_complete_hash_named_and_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _private_staging(monkeypatch, root)
    source = Path(agency_bootstrap_path())

    first = Path(launcher_bootstrap.stage_private_package_runtime(source))
    second = Path(launcher_bootstrap.prepare_private_package_runtime(first))

    assert first == second
    runtime_root = first.parents[2]
    assert runtime_root.name.startswith("runtime-sha256-")
    assert (runtime_root / "runtime-manifest.json").is_file()
    assert (runtime_root / "site-packages" / "yaml" / "__init__.py").is_file()
    assert not any(runtime_root.rglob("*.pth"))
    assert not any(runtime_root.rglob("*.pyc"))

    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(first),
            "agency_runtime.not_allowed",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert completed.returncode == 2
    assert completed.stderr.strip() == "Agency Runtime bootstrap rejected the module"
    assert "agency_runtime.server.dashboard_service" in isolated_bootstrap._ALLOWED_MODULES


def test_private_runtime_fast_reuse_rejects_bootstrap_and_manifest_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _private_staging(monkeypatch, root)
    staged = Path(launcher_bootstrap.stage_private_package_runtime(Path(agency_bootstrap_path())))

    original = staged.read_bytes()
    staged.write_text("tampered", encoding="utf-8")
    with pytest.raises(PermissionError, match="bootstrap does not match its manifest"):
        launcher_bootstrap.prepare_private_package_runtime(staged)
    staged.write_bytes(original)

    manifest = staged.parents[2] / "runtime-manifest.json"
    original_manifest = manifest.read_bytes()
    manifest.write_bytes(original_manifest + b" ")
    with pytest.raises(PermissionError, match="manifest artifact does not match"):
        launcher_bootstrap.prepare_private_package_runtime(staged)


def test_private_runtime_fast_reuse_needs_no_mutation_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _private_staging(monkeypatch, root)
    staged = Path(launcher_bootstrap.stage_private_package_runtime(Path(agency_bootstrap_path())))
    snapshots: list[Path] = []

    def snapshot(path: str | Path) -> SimpleNamespace:
        snapshots.append(Path(path))
        return _snapshot(path)

    def restricted(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("restricted tokens cannot mutate this owner-only projection")

    monkeypatch.setattr(launcher_bootstrap, "snapshot_persistent_artifact", snapshot)
    monkeypatch.setattr(launcher_bootstrap, "validate_private_directory", restricted)
    monkeypatch.setattr(launcher_bootstrap, "restrict_private_file", restricted)

    assert Path(launcher_bootstrap.prepare_private_package_runtime(staged)) == staged
    assert snapshots == [staged.parents[2] / "runtime-manifest.json", staged]


def test_private_runtime_fast_reuse_rejects_malformed_hash_named_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _private_staging(monkeypatch, root)
    staged = Path(launcher_bootstrap.stage_private_package_runtime(Path(agency_bootstrap_path())))
    runtime_root = staged.parents[2]
    manifest = runtime_root / "runtime-manifest.json"
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value["schema"] = "not-agency-runtime"
    malformed = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    manifest.write_bytes(malformed)
    renamed = runtime_root.with_name(f"runtime-sha256-{hashlib.sha256(malformed).hexdigest()}")
    runtime_root.rename(renamed)
    malformed_bootstrap = renamed / "site-packages" / "agency_runtime" / "_bootstrap.py"

    with pytest.raises(PermissionError, match="manifest contract is invalid"):
        launcher_bootstrap.prepare_private_package_runtime(malformed_bootstrap)


def test_private_runtime_full_publication_rejects_unmanifested_files_and_cleans_up(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _private_staging(monkeypatch, root)
    original_write = launcher_bootstrap._write_runtime_file

    def write_and_inject(path: Path, payload: bytes) -> None:
        original_write(path, payload)
        if path.name == "runtime-manifest.json":
            original_write(path.parent / "site-packages" / "injected.py", b"unsafe = True\n")

    monkeypatch.setattr(launcher_bootstrap, "_write_runtime_file", write_and_inject)

    with pytest.raises(PermissionError, match="outside its manifest"):
        launcher_bootstrap.stage_private_package_runtime(Path(agency_bootstrap_path()))
    assert list(root.iterdir()) == []


def test_private_runtime_staging_uses_the_guarded_parent_instead_of_per_file_acl_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _private_staging(monkeypatch, root)
    restricted_files: list[Path] = []
    monkeypatch.setattr(
        launcher_bootstrap,
        "restrict_private_file",
        lambda path: restricted_files.append(Path(path)),
    )

    staged = Path(launcher_bootstrap.stage_private_package_runtime(Path(agency_bootstrap_path())))

    assert len(restricted_files) == 1
    assert restricted_files[0].name == "runtime-manifest.json"
    assert restricted_files[0].parent.name.startswith(".runtime-stage-")
    assert staged.name == "_bootstrap.py"


def test_private_runtime_full_verification_rejects_a_changed_manifest_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _private_staging(monkeypatch, root)
    original_write = launcher_bootstrap._write_runtime_file

    def write_and_modify(path: Path, payload: bytes) -> None:
        original_write(path, payload)
        if path.name == "runtime-manifest.json":
            bootstrap = path.parent / "site-packages" / "agency_runtime" / "_bootstrap.py"
            bootstrap.write_bytes(bootstrap.read_bytes() + b"\n")

    monkeypatch.setattr(launcher_bootstrap, "_write_runtime_file", write_and_modify)

    with pytest.raises(PermissionError, match="does not match its manifest"):
        launcher_bootstrap.stage_private_package_runtime(Path(agency_bootstrap_path()))
    assert list(root.iterdir()) == []


def test_private_runtime_removes_a_published_projection_when_fast_attestation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _private_staging(monkeypatch, root)
    monkeypatch.setattr(
        launcher_bootstrap,
        "_verify_private_runtime_fast",
        lambda _path: (_ for _ in ()).throw(PermissionError("publication attestation failed")),
    )

    with pytest.raises(PermissionError, match="publication attestation failed"):
        launcher_bootstrap.stage_private_package_runtime(Path(agency_bootstrap_path()))
    assert list(root.iterdir()) == []


def test_private_runtime_rejects_arbitrary_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "private"
    _private_staging(monkeypatch, root, minimal_runtime=False)
    arbitrary = tmp_path / "_bootstrap.py"
    arbitrary.write_text("print('unsafe')", encoding="utf-8")

    with pytest.raises(PermissionError, match="limited to the active Agency package"):
        launcher_bootstrap.stage_private_package_runtime(arbitrary)
    with pytest.raises(PermissionError, match="not an Agency Runtime private projection"):
        launcher_bootstrap.verify_private_package_runtime(arbitrary)


def test_persistent_python_prefers_trusted_base_for_current_virtualenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = str(Path(sys.executable).absolute())
    base = str(Path(current).with_name("base-python.exe"))
    observed: list[str] = []

    def snapshot(path: str | Path, *, require_executable: bool = False) -> SimpleNamespace:
        observed.append(str(path))
        assert require_executable is True
        return SimpleNamespace(lexical_path=str(path))

    monkeypatch.setattr(launcher_bootstrap.sys, "_base_executable", base)
    monkeypatch.setattr(launcher_bootstrap, "snapshot_persistent_artifact", snapshot)

    assert launcher_bootstrap.persistent_python_executable(current) == base
    assert observed == [base]


def test_persistent_python_falls_back_to_current_when_base_is_untrusted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = str(Path(sys.executable).absolute())
    base = str(Path(current).with_name("unsafe-base-python.exe"))

    def snapshot(path: str | Path, *, require_executable: bool = False) -> SimpleNamespace:
        assert require_executable is True
        if str(path) == base:
            raise PermissionError("unsafe base namespace")
        return SimpleNamespace(lexical_path=str(path))

    monkeypatch.setattr(launcher_bootstrap.sys, "_base_executable", base)
    monkeypatch.setattr(launcher_bootstrap, "snapshot_persistent_artifact", snapshot)

    assert launcher_bootstrap.persistent_python_executable() == current


def test_persistent_python_never_substitutes_an_explicit_noncurrent_interpreter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    explicit = tmp_path / "requested-python"
    monkeypatch.setattr(
        launcher_bootstrap,
        "snapshot_persistent_artifact",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("unsafe explicit path")),
    )

    with pytest.raises(OSError, match="no trusted persistent Python executable"):
        launcher_bootstrap.persistent_python_executable(explicit)


def test_requirement_closure_ignores_unrequested_extras() -> None:
    distribution = SimpleNamespace(
        requires=[
            "PyYAML>=6",
            "coverage; extra == 'dev'",
            "colorama; sys_platform == 'win32'",
        ]
    )

    assert launcher_bootstrap._requirement_names(distribution) == (
        "PyYAML",
        "colorama",
    )
