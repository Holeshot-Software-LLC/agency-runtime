"""Private-directory portability for the deterministic delegation eval store."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from agency_runtime.core.evals import delegation
from tests.runtime_support import ensure_private_test_directory


def _private_eval_allocator(
    root: Path,
    observed: list[str],
):
    @contextmanager
    def allocate(*, prefix: str) -> Iterator[Path]:
        observed.append(prefix)
        candidate = root / f"{prefix}-{len(observed)}"
        ensure_private_test_directory(candidate)
        try:
            yield candidate
        finally:
            shutil.rmtree(candidate)

    return allocate


def test_eval_store_uses_private_allocator_and_cleans_up(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []
    monkeypatch.setattr(
        delegation,
        "private_temporary_directory",
        _private_eval_allocator(tmp_path, observed),
    )

    def inspect(store, adapter):
        assert adapter.store is store
        assert store.db_path.parent.name == "delegation-eval-1"
        assert store.database_stats()["tables"]["runs"] == 0
        return {"private": True}

    assert delegation._with_store(inspect) == {"private": True}
    assert observed == ["delegation-eval"]
    assert not (tmp_path / "delegation-eval-1").exists()


def test_eval_store_cleanup_preserves_callback_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []
    monkeypatch.setattr(
        delegation,
        "private_temporary_directory",
        _private_eval_allocator(tmp_path, observed),
    )

    def fail(_store, _adapter):
        raise RuntimeError("expected")

    with pytest.raises(RuntimeError, match="expected"):
        delegation._with_store(fail)

    assert observed == ["delegation-eval"]
    assert not (tmp_path / "delegation-eval-1").exists()
