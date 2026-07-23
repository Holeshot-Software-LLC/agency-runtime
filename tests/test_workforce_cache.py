from __future__ import annotations

import json

import pytest

from agency_runtime.core.workforce import cache


def test_cache_identity_is_stage_scoped_canonical_and_content_free() -> None:
    left = cache.workforce_cache_identity(
        "plan",
        {"request_hash": "sha256:abc", "nested": {"b": 2, "a": 1}},
    )
    reordered = cache.workforce_cache_identity(
        "plan",
        {"nested": {"a": 1, "b": 2}, "request_hash": "sha256:abc"},
    )
    other_stage = cache.workforce_cache_identity(
        "candidate",
        {"request_hash": "sha256:abc", "nested": {"a": 1, "b": 2}},
    )

    assert left == reordered
    assert left != other_stage
    assert "abc" not in left.key
    assert len(left.digest) == 64


def test_cache_values_are_detached_bounded_and_expire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = {"value": 10.0}
    monkeypatch.setattr(cache.time, "monotonic", lambda: now["value"])
    monkeypatch.setattr(cache, "WORKFORCE_CACHE_MAX_ENTRIES_PER_STAGE", 2)
    first = cache.workforce_cache_identity("plan", {"id": 1})
    second = cache.workforce_cache_identity("plan", {"id": 2})
    third = cache.workforce_cache_identity("plan", {"id": 3})
    value = {"items": ["one"]}

    cache.workforce_cache_put(first, value)
    value["items"].append("caller-mutation")
    assert cache.workforce_cache_get(first) == {"items": ["one"]}
    detached = cache.workforce_cache_get(first)
    detached["items"].append("read-mutation")
    assert cache.workforce_cache_get(first) == {"items": ["one"]}

    cache.workforce_cache_put(second, {"id": 2})
    cache.workforce_cache_put(third, {"id": 3})
    assert cache.workforce_cache_get(first) is None
    assert cache.workforce_cache_counts()["plan"] == 2

    now["value"] += cache.WORKFORCE_CACHE_TTL_SECONDS + 1
    assert cache.workforce_cache_get(second) is None


@pytest.mark.parametrize("stage", ["", "planner", "unknown"])
def test_cache_rejects_unknown_stages(stage: str) -> None:
    with pytest.raises(ValueError, match="stage"):
        cache.workforce_cache_identity(stage, {})


def test_cache_rejects_noncanonical_or_oversized_identity() -> None:
    with pytest.raises(TypeError, match="mapping"):
        cache.workforce_cache_identity("plan", [])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="canonical JSON"):
        cache.workforce_cache_identity("plan", {"value": float("nan")})
    with pytest.raises(ValueError, match="size bound"):
        cache.workforce_cache_identity("plan", {"value": "x" * (512 * 1024)})
    with pytest.raises(ValueError, match="canonical JSON"):
        cache.workforce_cache_identity("plan", {"value": json})


def test_cache_requires_typed_identity() -> None:
    with pytest.raises(TypeError, match="cache identity"):
        cache.workforce_cache_get("plan")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="cache identity"):
        cache.workforce_cache_put("plan", {})  # type: ignore[arg-type]
