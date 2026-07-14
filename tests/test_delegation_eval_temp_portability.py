"""Restricted-token portability for the deterministic delegation eval store."""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.core.evals import delegation


def test_eval_temp_directory_retries_collisions_and_cleans_up(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collision = tmp_path / "agency-delegation-eval-collision"
    collision.mkdir()
    tokens = iter(["collision", "unique"])
    monkeypatch.setattr(delegation.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(delegation.secrets, "token_hex", lambda _size: next(tokens))

    with delegation._temporary_eval_directory() as candidate:
        assert candidate == tmp_path / "agency-delegation-eval-unique"
        assert candidate.is_dir()
        (candidate / "synthetic.db").write_bytes(b"test")

    assert collision.is_dir()
    assert not (tmp_path / "agency-delegation-eval-unique").exists()


def test_eval_temp_directory_cleans_up_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(delegation.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(delegation.secrets, "token_hex", lambda _size: "failure")
    candidate = tmp_path / "agency-delegation-eval-failure"

    with (
        pytest.raises(RuntimeError, match="expected"),
        delegation._temporary_eval_directory() as allocated,
    ):
        assert allocated == candidate
        raise RuntimeError("expected")

    assert not candidate.exists()


def test_eval_temp_directory_fails_after_bounded_collision_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collision = tmp_path / "agency-delegation-eval-collision"
    collision.mkdir()
    monkeypatch.setattr(delegation.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(delegation.secrets, "token_hex", lambda _size: "collision")

    with (
        pytest.raises(RuntimeError, match="unique delegation eval directory"),
        delegation._temporary_eval_directory(),
    ):
        pass


def test_synthetic_eval_store_retains_link_checks_without_acl_mutation(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.db"
    store = delegation._SyntheticEvalStore(path)
    assert store.database_stats()["tables"]["runs"] == 0
    assert path.is_file()
