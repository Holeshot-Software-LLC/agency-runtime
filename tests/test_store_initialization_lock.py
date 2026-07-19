"""SQLite constructor serialization and durable lock security regressions."""

from __future__ import annotations

import json
import math
import os
import sqlite3
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.store import initialization_lock as init_lock
from agency_runtime.core.store.sqlite import Store


def _failing_creator(
    db_path: str,
    entered: Any,
    release: Any,
    completed: Any,
    result_path: str,
) -> None:
    """Spawn-safe creator that fails only after its new DB is visible."""

    original = Store._init_schema

    def fail_after_create(self: Store, **_kwargs: object) -> None:
        entered.set()
        if not release.wait(timeout=20):
            raise RuntimeError("test release timed out")
        raise RuntimeError("intentional first-constructor failure")

    Store._init_schema = fail_after_create
    try:
        Store(Path(db_path))
    except BaseException as exc:
        result = ("first", type(exc).__name__, str(exc))
    else:
        result = ("first", "unexpected-success", "")
    finally:
        Store._init_schema = original
        Path(result_path).write_text(json.dumps(result), encoding="utf-8")
        completed.set()


def _successful_creator(
    db_path: str,
    started: Any,
    completed: Any,
    result_path: str,
) -> None:
    """Spawn-safe constructor that must wait for the failed creator rollback."""

    started.set()
    try:
        Store(Path(db_path))
    except BaseException as exc:
        result = ("second", type(exc).__name__, str(exc))
    else:
        result = ("second", "success", "")
    finally:
        Path(result_path).write_text(json.dumps(result), encoding="utf-8")
        completed.set()


def test_initialization_lock_path_is_bounded_stable_and_path_scoped(tmp_path: Path) -> None:
    first = init_lock.initialization_lock_path(tmp_path / "first.db")
    repeated = init_lock.initialization_lock_path(tmp_path / "first.db")
    second = init_lock.initialization_lock_path(tmp_path / "second.db")

    assert first == repeated
    assert first != second
    assert first.parent == tmp_path
    assert first.name.startswith(".agency-init-")
    assert len(first.name) < 100


@pytest.mark.parametrize("timeout", [True, -1, math.inf, math.nan, 301])
def test_initialization_lock_rejects_invalid_timeout(
    tmp_path: Path,
    timeout: object,
) -> None:
    with (
        pytest.raises(ValueError, match="between 0 and 300"),
        init_lock.storage_initialization_lock(  # type: ignore[arg-type]
            tmp_path / "agency.db",
            timeout=timeout,
        ),
    ):
        pytest.fail("invalid timeout must not acquire")


def test_initialization_lock_is_persistent_private_and_reentrant_after_release(
    tmp_path: Path,
) -> None:
    database = tmp_path / "agency.db"
    with init_lock.storage_initialization_lock(database) as first_path:
        assert first_path == init_lock.initialization_lock_path(database)
        assert first_path.stat().st_size == 1

    assert first_path.exists()
    with init_lock.storage_initialization_lock(database, timeout=0.5) as second_path:
        assert second_path == first_path


def test_second_initialization_lock_times_out_without_splitting_inode(tmp_path: Path) -> None:
    database = tmp_path / "agency.db"
    lock_path = init_lock.initialization_lock_path(database)

    with init_lock.storage_initialization_lock(database):
        before = lock_path.stat()
        with (
            pytest.raises(init_lock.StorageInitializationBusyError, match="busy"),
            init_lock.storage_initialization_lock(database, timeout=0),
        ):
            pytest.fail("a second owner must not enter")
        after = lock_path.stat()
        assert os.path.samestat(before, after)


def test_initialization_lock_rejects_invalid_persistent_content(tmp_path: Path) -> None:
    database = tmp_path / "agency.db"
    lock_path = init_lock.initialization_lock_path(database)
    lock_path.write_bytes(b"not-one-byte")

    with (
        pytest.raises(
            init_lock.StorageInitializationLockSecurityError,
            match="invalid content length",
        ),
        init_lock.storage_initialization_lock(database),
    ):
        pytest.fail("invalid lock file must not acquire")


def test_failed_creator_rolls_back_before_second_constructor_can_adopt(
    tmp_path: Path,
) -> None:
    """A failed creator retains the lock until its exact rollback completes."""

    database = tmp_path / "concurrent.db"
    context = get_context("spawn")
    first_entered = context.Event()
    first_release = context.Event()
    first_done = context.Event()
    second_started = context.Event()
    second_done = context.Event()
    first_result = tmp_path / "first-result.json"
    second_result = tmp_path / "second-result.json"
    first = context.Process(
        target=_failing_creator,
        args=(str(database), first_entered, first_release, first_done, str(first_result)),
    )
    second = context.Process(
        target=_successful_creator,
        args=(str(database), second_started, second_done, str(second_result)),
    )
    started_processes = []
    try:
        first.start()
        started_processes.append(first)
        assert first_entered.wait(timeout=20)
        assert database.exists()

        second.start()
        started_processes.append(second)
        assert second_started.wait(timeout=10)
        assert not second_done.wait(timeout=0.4)
        assert not first_result.exists()
        assert not second_result.exists()

        first_release.set()
        for process in started_processes:
            process.join(timeout=30)
            assert process.exitcode == 0
        assert first_done.is_set()
        assert second_done.is_set()
    finally:
        first_release.set()
        for process in started_processes:
            if process.is_alive():
                process.terminate()
            process.join(timeout=5)

    messages = [
        json.loads(first_result.read_text(encoding="utf-8")),
        json.loads(second_result.read_text(encoding="utf-8")),
    ]
    by_worker = {message[0]: tuple(message[1:]) for message in messages}
    assert by_worker["first"] == (
        "RuntimeError",
        "intentional first-constructor failure",
    )
    assert by_worker["second"] == ("success", "")

    connection = sqlite3.connect(database)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("SELECT version FROM schema_version").fetchone() is not None
    finally:
        connection.close()
