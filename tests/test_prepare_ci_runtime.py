"""Hosted-CI private runtime preparation contracts."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest

from agency_runtime.core.process_argv import snapshot_persistent_artifact
from scripts import ci_private_node, parallel_change_loop_storage, prepare_ci_runtime
from tests import runtime_support


def _fake_node(tmp_path: Path, payload: bytes = b"fake-node-runtime") -> Path:
    source = tmp_path / ("source-node.exe" if os.name == "nt" else "source-node")
    source.write_bytes(payload)
    source.chmod(0o700)
    return source


def _resolver(source: Path):
    return lambda name: str(source) if name == "node" else None


def test_prepare_ci_runtime_is_private_real_and_idempotent(tmp_path: Path) -> None:
    first = prepare_ci_runtime.prepare_ci_runtime(
        "py3.10-linux",
        home_dir=tmp_path,
        node_resolver=lambda _name: None,
    )
    second = prepare_ci_runtime.prepare_ci_runtime(
        "py3.10-linux",
        home_dir=tmp_path,
        node_resolver=lambda _name: None,
    )

    assert first == second
    root = Path(first["AGENCY_CI_ROOT"])
    python = Path(first["AGENCY_CI_PYTHON"])
    lock = root.parent / ".py3.10-linux.prepare.lock"
    assert root.is_dir() and not root.is_symlink()
    assert python.is_file() and not python.is_symlink()
    assert lock.is_file() and not lock.is_symlink()
    assert lock.read_bytes() == b"\0"
    assert python.resolve(strict=True).is_relative_to(root)
    assert snapshot_persistent_artifact(python, require_executable=True).resolved_path == str(
        python.resolve(strict=True)
    )
    if os.name != "nt":
        assert stat.S_IMODE(root.stat().st_mode) == 0o700
        assert stat.S_IMODE(lock.stat().st_mode) == 0o600
        assert not stat.S_IMODE(python.stat().st_mode) & (stat.S_IWGRP | stat.S_IWOTH)
    completed = subprocess.run(
        [str(python), "-I", "-c", "import json; print(json.dumps({'ok': True}))"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout) == {"ok": True}
    assert completed.stderr == ""


def test_prepare_ci_runtime_bootstraps_only_its_profile_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bootstrapped: list[Path] = []
    original = prepare_ci_runtime.ensure_private_directory

    def bootstrap(path: Path) -> Path:
        bootstrapped.append(path)
        return original(path)

    monkeypatch.setattr(prepare_ci_runtime, "bootstrap_private_directory", bootstrap)

    values = prepare_ci_runtime.prepare_ci_runtime(
        "bootstrap-route",
        home_dir=tmp_path,
        node_resolver=lambda _name: None,
    )

    assert bootstrapped == [tmp_path.resolve() / ".agency-runtime-ci"]
    assert Path(values["AGENCY_CI_ROOT"]).is_relative_to(bootstrapped[0])


def test_ci_bootstrap_request_is_direct_and_probe_free_off_windows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        prepare_ci_runtime,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: pytest.fail("non-Windows request probed Windows trust"),
    )
    monkeypatch.setattr(
        prepare_ci_runtime,
        "current_process_user_sid",
        lambda **_kwargs: pytest.fail("non-Windows request probed a Windows SID"),
    )

    assert prepare_ci_runtime._ci_bootstrap_request(
        tmp_path.resolve(),
        is_windows=False,
    ) == (tmp_path.resolve() / ".agency-runtime-ci")


def test_ci_bootstrap_request_uses_a_trusted_windows_profile_without_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        prepare_ci_runtime,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        prepare_ci_runtime,
        "current_process_user_sid",
        lambda **_kwargs: pytest.fail("trusted Windows profile probed a SID"),
    )

    assert prepare_ci_runtime._ci_bootstrap_request(
        tmp_path.resolve(),
        is_windows=True,
    ) == (tmp_path.resolve() / ".agency-runtime-ci")


def test_ci_bootstrap_request_relocates_untrusted_windows_profile_deterministically(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "Users" / "runneradmin"
    home.mkdir(parents=True)
    requested = home.resolve() / ".agency-runtime-ci"
    trust_probes: list[Path] = []

    def trusted(path: Path, **_kwargs: object) -> bool:
        trust_probes.append(path)
        return path == home.parent.resolve()

    monkeypatch.setattr(
        prepare_ci_runtime,
        "storage_parent_is_trusted",
        trusted,
    )
    monkeypatch.setattr(
        prepare_ci_runtime,
        "current_process_user_sid",
        lambda **_kwargs: "S-1-5-21-42",
    )

    first = prepare_ci_runtime._ci_bootstrap_request(home.resolve(), is_windows=True)
    second = prepare_ci_runtime._ci_bootstrap_request(home.resolve(), is_windows=True)

    digest = sha256(f"S-1-5-21-42\0{requested.as_posix().casefold()}".encode()).hexdigest()[:32]
    expected = home.parent.resolve() / f".agency-runtime-ci-{digest}"
    assert first == second == expected
    assert trust_probes == [home.resolve(), home.parent.resolve()] * 2
    assert "S-1-5-21-42" not in first.name


def test_ci_bootstrap_request_changes_with_windows_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "Users" / "runneradmin"
    home.mkdir(parents=True)
    monkeypatch.setattr(
        prepare_ci_runtime,
        "storage_parent_is_trusted",
        lambda path, **_kwargs: path == home.parent.resolve(),
    )
    identity = iter(("S-1-5-21-42", "S-1-5-21-43"))
    monkeypatch.setattr(
        prepare_ci_runtime,
        "current_process_user_sid",
        lambda **_kwargs: next(identity),
    )

    first = prepare_ci_runtime._ci_bootstrap_request(home.resolve(), is_windows=True)
    second = prepare_ci_runtime._ci_bootstrap_request(home.resolve(), is_windows=True)

    assert first != second
    assert first.parent == second.parent == home.parent.resolve()


def test_ci_bootstrap_request_fails_closed_without_identity_or_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "Users" / "runneradmin"
    home.mkdir(parents=True)
    monkeypatch.setattr(
        prepare_ci_runtime,
        "storage_parent_is_trusted",
        lambda path, **_kwargs: path == home.parent.resolve(),
    )
    monkeypatch.setattr(
        prepare_ci_runtime,
        "current_process_user_sid",
        lambda **_kwargs: None,
    )
    with pytest.raises(RuntimeError, match="identify the current Windows user"):
        prepare_ci_runtime._ci_bootstrap_request(home.resolve(), is_windows=True)

    monkeypatch.setattr(
        prepare_ci_runtime,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        prepare_ci_runtime,
        "current_process_user_sid",
        lambda **_kwargs: pytest.fail("untrusted path probed a SID"),
    )
    with pytest.raises(RuntimeError, match="no trusted Windows creation boundary"):
        prepare_ci_runtime._ci_bootstrap_request(home.resolve(), is_windows=True)


@pytest.mark.parametrize("label", ["", "../escape", "space here", "x" * 81])
def test_prepare_ci_runtime_rejects_unsafe_labels(tmp_path: Path, label: str) -> None:
    with pytest.raises(ValueError, match="filesystem-safe"):
        prepare_ci_runtime.prepare_ci_runtime(label, home_dir=tmp_path)


def test_prepare_ci_runtime_rejects_tampered_interpreter_without_following_link(
    tmp_path: Path,
) -> None:
    values = prepare_ci_runtime.prepare_ci_runtime(
        "tamper-test",
        home_dir=tmp_path,
        node_resolver=lambda _name: None,
    )
    python = Path(values["AGENCY_CI_PYTHON"])
    outside = tmp_path / "outside-python"
    sentinel = b"do-not-overwrite"
    outside.write_bytes(sentinel)
    python.unlink()
    try:
        python.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    with pytest.raises(RuntimeError, match="incomplete or unsafe"):
        prepare_ci_runtime.prepare_ci_runtime("tamper-test", home_dir=tmp_path)
    assert outside.read_bytes() == sentinel


def test_prepare_ci_runtime_rejects_lock_symlink_without_touching_target(
    tmp_path: Path,
) -> None:
    base = prepare_ci_runtime._private_directory(tmp_path / ".agency-runtime-ci")
    victim = tmp_path / "lock-victim"
    victim.write_bytes(b"do-not-touch")
    lock = base / ".symlink-lock.prepare.lock"
    try:
        lock.symlink_to(victim)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    with pytest.raises(RuntimeError, match="preparation lock"):
        prepare_ci_runtime.prepare_ci_runtime(
            "symlink-lock",
            home_dir=tmp_path,
            node_resolver=lambda _name: None,
        )

    assert victim.read_bytes() == b"do-not-touch"


def test_isolated_runtime_attests_site_mode_and_rejects_wrong_reuse(tmp_path: Path) -> None:
    values = prepare_ci_runtime.prepare_ci_runtime(
        "isolated-mode",
        home_dir=tmp_path,
        node_resolver=lambda _name: None,
        system_site_packages=False,
    )
    configuration = Path(values["AGENCY_CI_ROOT"]) / "venv" / "pyvenv.cfg"
    assert "include-system-site-packages = false" in configuration.read_text("utf-8").lower()
    with pytest.raises(RuntimeError, match="wrong isolation mode"):
        prepare_ci_runtime.prepare_ci_runtime(
            "isolated-mode",
            home_dir=tmp_path,
            node_resolver=lambda _name: None,
            system_site_packages=True,
        )


def test_contract_rebuild_refuses_unknown_private_collision(tmp_path: Path) -> None:
    base = prepare_ci_runtime._private_directory(tmp_path / ".agency-runtime-ci")
    collision = prepare_ci_runtime._private_directory(base / "contract-collision")
    sentinel = collision / "user-sentinel"
    sentinel.write_bytes(b"do-not-delete")

    with pytest.raises(RuntimeError, match="not Agency-owned"):
        prepare_ci_runtime.prepare_ci_runtime(
            "contract-collision",
            home_dir=tmp_path,
            node_resolver=lambda _name: None,
            system_site_packages=False,
            runtime_contract="a" * 64,
        )

    assert sentinel.read_bytes() == b"do-not-delete"


def test_exact_receipt_publication_failure_rolls_back_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = prepare_ci_runtime._private_directory(tmp_path / "receipt-parent")
    receipt = parent / "receipt"
    original = parallel_change_loop_storage.exact_private_file_is_valid
    monkeypatch.setattr(
        parallel_change_loop_storage,
        "exact_private_file_is_valid",
        lambda *_args, **_kwargs: False,
    )
    with pytest.raises(RuntimeError, match="could not be attested"):
        parallel_change_loop_storage.create_exact_private_file(receipt, b"receipt\n")
    assert not receipt.exists()

    monkeypatch.setattr(parallel_change_loop_storage, "exact_private_file_is_valid", original)
    parallel_change_loop_storage.create_exact_private_file(receipt, b"receipt\n")
    assert receipt.read_bytes() == b"receipt\n"


def test_shared_lock_cleanup_preserves_primary_and_exposes_bounded_standalone_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = prepare_ci_runtime._private_directory(tmp_path / "lock-parent")
    lock = parent / "shared.lock"
    monkeypatch.setattr(
        parallel_change_loop_storage,
        "_unlock",
        lambda _handle: (_ for _ in ()).throw(OSError("sensitive unlock detail")),
    )

    with (
        pytest.raises(ValueError, match="primary") as primary,
        parallel_change_loop_storage.private_runtime_lock(
            lock,
            wait_seconds=0,
            busy_message="busy",
        ),
    ):
        raise ValueError("primary")
    assert any("parallel lock cleanup failed (OSError)" in note for note in primary.value.__notes__)
    assert all("sensitive unlock detail" not in note for note in primary.value.__notes__)

    with (
        pytest.raises(parallel_change_loop_storage.PrivateRuntimeLockCleanupError) as cleanup,
        parallel_change_loop_storage.private_runtime_lock(
            lock,
            wait_seconds=0,
            busy_message="busy",
        ),
    ):
        pass
    assert cleanup.value.failure_category == "cleanup"
    assert cleanup.value.cleanup_component == "lock"


def test_private_node_copy_is_real_owner_only_and_idempotent(tmp_path: Path) -> None:
    source = _fake_node(tmp_path)
    root = prepare_ci_runtime._private_directory(tmp_path / "private-runtime")

    first = ci_private_node.prepare_private_node(root, resolver=_resolver(source))
    second = ci_private_node.prepare_private_node(root, resolver=_resolver(source))

    assert first == second
    assert first is not None
    assert first != source
    assert first.is_file() and not first.is_symlink()
    assert first.read_bytes() == source.read_bytes()
    assert first.resolve(strict=True).is_relative_to(root)
    identity = snapshot_persistent_artifact(first, require_executable=True)
    assert identity.resolved_path == str(first.resolve(strict=True))
    if os.name != "nt":
        assert stat.S_IMODE(first.stat().st_mode) == 0o700
        assert stat.S_IMODE((first.parent / "node-copy.json").stat().st_mode) == 0o600


def test_private_node_copy_rejects_target_tamper_and_source_change(tmp_path: Path) -> None:
    source = _fake_node(tmp_path)
    target_root = prepare_ci_runtime._private_directory(tmp_path / "target-runtime")
    target = ci_private_node.prepare_private_node(target_root, resolver=_resolver(source))
    assert target is not None
    target.write_bytes(b"tampered-private-copy")
    target.chmod(0o700)

    with pytest.raises(RuntimeError, match="replaced or modified"):
        ci_private_node.prepare_private_node(target_root, resolver=_resolver(source))

    source_root = prepare_ci_runtime._private_directory(tmp_path / "source-runtime")
    unchanged_target = ci_private_node.prepare_private_node(
        source_root,
        resolver=_resolver(source),
    )
    assert unchanged_target is not None
    original_copy = unchanged_target.read_bytes()
    source.write_bytes(b"changed-host-node-source")
    source.chmod(0o700)

    with pytest.raises(RuntimeError, match="source changed"):
        ci_private_node.prepare_private_node(source_root, resolver=_resolver(source))
    assert unchanged_target.read_bytes() == original_copy


def test_private_node_copy_rejects_incomplete_collision(tmp_path: Path) -> None:
    source = _fake_node(tmp_path)
    root = prepare_ci_runtime._private_directory(tmp_path / "collision-runtime")
    binary_directory = prepare_ci_runtime._private_directory(root / "bin")
    target = binary_directory / ("node.exe" if os.name == "nt" else "node")
    target.write_bytes(b"preexisting")
    target.chmod(0o700)

    with pytest.raises(RuntimeError, match="incomplete path collision"):
        ci_private_node.prepare_private_node(root, resolver=_resolver(source))


def test_prepare_ci_runtime_exports_private_node_to_github_environment(tmp_path: Path) -> None:
    source = _fake_node(tmp_path)
    values = prepare_ci_runtime.prepare_ci_runtime(
        "node-environment",
        home_dir=tmp_path,
        node_resolver=_resolver(source),
    )
    target = Path(values["AGENCY_CI_NODE"])
    assert target.read_bytes() == source.read_bytes()

    github_environment = tmp_path / "github-node.env"
    prepare_ci_runtime._write_github_environment(github_environment, values)
    assert f"AGENCY_CI_NODE={target.as_posix()}\n" in github_environment.read_text("utf-8")


def test_trusted_test_interpreter_prefers_private_ci_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = tmp_path / "runtime with spaces" / "python"
    monkeypatch.setenv("AGENCY_CI_PYTHON", str(configured))

    assert runtime_support.trusted_test_interpreter() == configured.resolve()


def test_product_environment_isolation_preserves_ci_runtime_authority() -> None:
    assert runtime_support.is_agency_product_environment_key("AGENCY_CONFIG_PATH")
    assert runtime_support.is_agency_product_environment_key("AGENCY_DB_PATH")
    assert not runtime_support.is_agency_product_environment_key("AGENCY_CI_NODE")
    assert not runtime_support.is_agency_product_environment_key("AGENCY_CI_PYTHON")


def test_github_environment_writer_is_append_only_and_rejects_injection(
    tmp_path: Path,
) -> None:
    target = tmp_path / "github.env"
    target.write_text("EXISTING=value\n", encoding="utf-8")
    prepare_ci_runtime._write_github_environment(
        target,
        {"AGENCY_CI_ROOT": tmp_path.as_posix()},
    )
    assert target.read_text(encoding="utf-8") == (
        f"EXISTING=value\nAGENCY_CI_ROOT={tmp_path.as_posix()}\n"
    )

    with pytest.raises(RuntimeError, match="line breaks"):
        prepare_ci_runtime._write_github_environment(target, {"BAD": "line\nbreak"})

    link = tmp_path / "link.env"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")
    with pytest.raises(RuntimeError, match="symlink"):
        prepare_ci_runtime._write_github_environment(link, {"BAD": "value"})
