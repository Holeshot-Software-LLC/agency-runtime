"""Receipt and failure-isolation coverage for private path authorities."""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.core import path_authority, private_paths


@pytest.fixture(autouse=True)
def _isolated_authorities(monkeypatch: pytest.MonkeyPatch) -> None:
    path_authority._AUTHORITIES.clear()
    monkeypatch.setattr(private_paths, "reattest_codex_host_private_path", lambda _path: False)
    yield
    path_authority._AUTHORITIES.clear()


def test_authority_covers_exact_root_and_descendants(tmp_path: Path) -> None:
    root = tmp_path / "private"
    observed: list[Path] = []

    def probe(target: Path) -> bool:
        observed.append(target)
        return True

    path_authority.register_private_path_authority(root, probe)

    assert path_authority.private_path_authority_covers(root)
    assert path_authority.private_path_authority_covers(root / "nested")
    assert observed == [root, root / "nested"]


def test_authority_ignores_unrelated_paths_and_probe_failures(tmp_path: Path) -> None:
    root = tmp_path / "private"
    called = False

    def exploding_probe(_target: Path) -> bool:
        nonlocal called
        called = True
        raise RuntimeError("stale receipt")

    path_authority.register_private_path_authority(root, exploding_probe)

    assert not path_authority.private_path_authority_covers(tmp_path / "peer")
    assert called is False
    assert not path_authority.private_path_authority_covers(root / "nested")
    assert called is True


def test_false_probe_falls_through_to_later_authority(tmp_path: Path) -> None:
    outer = tmp_path / "private"
    inner = outer / "nested"
    path_authority.register_private_path_authority(outer, lambda _target: False)
    path_authority.register_private_path_authority(inner, lambda _target: True)

    assert path_authority.private_path_authority_covers(inner / "leaf")


def test_discard_requires_matching_probe_when_supplied(tmp_path: Path) -> None:
    root = tmp_path / "private"

    def original(_target: Path) -> bool:
        return True

    def replacement(_target: Path) -> bool:
        return False

    path_authority.register_private_path_authority(root, original)

    path_authority.discard_private_path_authority(root, replacement)
    assert path_authority.private_path_authority_covers(root)

    path_authority.discard_private_path_authority(root, original)
    assert not path_authority.private_path_authority_covers(root)

    path_authority.register_private_path_authority(root, original)
    path_authority.discard_private_path_authority(root)
    assert not path_authority.private_path_authority_covers(root)


def test_paths_are_normalized_before_registration_and_lookup(
    tmp_path: Path,
) -> None:
    root_with_parent_segment = tmp_path / "private" / ".." / "private"

    path_authority.register_private_path_authority(root_with_parent_segment, lambda _: True)

    assert path_authority.private_path_authority_covers(tmp_path / "private" / "child")
