"""A card returns to the cabinet at turn end, and the next turn is told so.

Vision rule 7 is "vampire an employee for a turn and spit him out". The
bookkeeping half already worked -- ``specialists_loaded.expired_at`` is stamped
at turn close -- but on hosts where injected context cannot be retracted, an
expired specialist stays legible further up the conversation and keeps steering
the generalist. Expiry that is recorded but never stated is not expiry.

These tests pin the three properties that make the announcement safe to ship:
it is content-free, it is announced once rather than accumulating, and it can
never cost a turn.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agency_runtime.core.specialist_context import (
    MAX_EXPIRED_SPECIALIST_ANNOUNCEMENTS,
    format_expired_specialist_context,
)
from agency_runtime.core.store.sqlite import Store


def _load(store: Store, session_id: str, trace_id: str, *slugs: str) -> None:
    for slug in slugs:
        store.record_specialist_loaded(session_id, slug, trace_id=trace_id)


def _expire(store: Store, session_id: str, trace_id: str) -> None:
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE specialists_loaded SET expired_at = ? "
            "WHERE session_id = ? AND trace_id = ? AND expired_at IS NULL",
            ("2026-08-07T00:00:00Z", session_id, trace_id),
        )
        conn.commit()
    finally:
        conn.close()


def test_previous_turn_expired_card_is_announced_to_the_next_turn(tmp_path: Path) -> None:
    store = Store(tmp_path / "expiry.db")
    _load(store, "session", "turn-1", "database-optimizer")
    _expire(store, "session", "turn-1")
    _load(store, "session", "turn-2", "frontend-developer")

    announced = store.get_expired_specialists_to_announce("session", "turn-2")

    assert announced == ["database-optimizer"]


def test_a_card_reselected_this_turn_is_never_announced_as_expired(tmp_path: Path) -> None:
    """Re-hiring the same specialist means it is live again, not spat out."""

    store = Store(tmp_path / "reselected.db")
    _load(store, "session", "turn-1", "database-optimizer", "frontend-developer")
    _expire(store, "session", "turn-1")
    _load(store, "session", "turn-2", "database-optimizer")

    announced = store.get_expired_specialists_to_announce("session", "turn-2")

    assert announced == ["frontend-developer"]


def test_expiry_is_announced_once_rather_than_accumulating(tmp_path: Path) -> None:
    """The guard against becoming the context bloat this exists to prevent.

    Only the immediately preceding turn is considered, so a card is named on
    exactly one subsequent turn instead of growing a tombstone list that is
    re-injected for the rest of the session.
    """

    store = Store(tmp_path / "once.db")
    _load(store, "session", "turn-1", "database-optimizer")
    _expire(store, "session", "turn-1")
    _load(store, "session", "turn-2", "frontend-developer")
    _expire(store, "session", "turn-2")
    _load(store, "session", "turn-3", "code-reviewer")

    # turn-3 hears about turn-2's card only. turn-1's is long gone.
    assert store.get_expired_specialists_to_announce("session", "turn-3") == [
        "frontend-developer"
    ]


def test_first_turn_of_a_session_announces_nothing(tmp_path: Path) -> None:
    store = Store(tmp_path / "first.db")
    _load(store, "session", "turn-1", "database-optimizer")

    assert store.get_expired_specialists_to_announce("session", "turn-1") == []


def test_a_still_live_previous_card_is_not_announced(tmp_path: Path) -> None:
    """Only expiry is announced. An unexpired row is a turn still in flight."""

    store = Store(tmp_path / "live.db")
    _load(store, "session", "turn-1", "database-optimizer")
    _load(store, "session", "turn-2", "frontend-developer")

    assert store.get_expired_specialists_to_announce("session", "turn-2") == []


def test_announcement_is_identity_only_and_never_repeats_a_prompt_body() -> None:
    """The whole point of naming rather than re-injecting: cost stays one line."""

    context = format_expired_specialist_context(["database-optimizer", "code-reviewer"])

    assert "database-optimizer" in context
    assert "code-reviewer" in context
    assert "[AGENCY SPECIALIST EXPIRY]" in context
    assert "expired" in context
    # A card body is thousands of characters; an expiry notice must not be.
    assert len(context) < 512


def test_announcement_is_bounded_and_deduplicated() -> None:
    slugs = [f"specialist-{index}" for index in range(50)]
    context = format_expired_specialist_context([*slugs, *slugs])

    named = [slug for slug in slugs if slug in context]
    assert len(named) == MAX_EXPIRED_SPECIALIST_ANNOUNCEMENTS


def test_resident_managers_are_never_announced_as_expired() -> None:
    """Residents are not cards; they do not get hired or spat out."""

    assert format_expired_specialist_context(["agency-steward"]) == ""


def test_nothing_expired_produces_no_context_at_all() -> None:
    assert format_expired_specialist_context([]) == ""
    assert format_expired_specialist_context(["", "   "]) == ""


def test_a_store_that_cannot_answer_never_costs_the_turn() -> None:
    """Fail-open: an expiry notice is a courtesy, never a precondition."""

    from agency_runtime.adapters.base import BaseAdapter

    class _ExplodingStore:
        def get_expired_specialists_to_announce(self, *_args: Any, **_kwargs: Any) -> list[str]:
            raise RuntimeError("store is unavailable")

    class _Adapter(BaseAdapter):
        host_name = "claude"

        def __init__(self) -> None:
            self._store = _ExplodingStore()

        @property
        def store(self) -> Any:
            return self._store

        def is_available(self) -> bool:
            return True

        def get_delegate_backend(self) -> str | None:
            return None

    assert _Adapter()._expired_specialist_notice("session", "trace") == ""


def test_a_store_without_the_reader_is_tolerated() -> None:
    """Older stores simply do not announce; they must not raise."""

    from agency_runtime.adapters.base import BaseAdapter

    class _Adapter(BaseAdapter):
        host_name = "claude"

        @property
        def store(self) -> Any:
            return object()

        def is_available(self) -> bool:
            return True

        def get_delegate_backend(self) -> str | None:
            return None

    assert _Adapter()._expired_specialist_notice("session", "trace") == ""


def test_expiry_notice_reaches_the_delivered_context(monkeypatch: Any) -> None:
    """End-to-end wiring: the notice is appended to what the host actually gets.

    build_preflight_context is the single path every host shares -- the Claude
    and Codex hooks, the OpenClaw typed plugin, and the Hermes bridge all end up
    here -- so wiring expiry at this level is what makes rule 9 parity hold
    without a per-host branch.
    """

    from agency_runtime.adapters.base import BaseAdapter

    class _Store:
        def get_expired_specialists_to_announce(self, *_args: Any, **_kwargs: Any) -> list[str]:
            return ["database-optimizer"]

    class _Adapter(BaseAdapter):
        host_name = "claude"

        @property
        def store(self) -> Any:
            return _Store()

        def is_available(self) -> bool:
            return True

        def get_delegate_backend(self) -> str | None:
            return None

        def runtime_enabled(self) -> bool:
            return True

    class _Result:
        def as_dict(self) -> dict[str, Any]:
            return {"context": "[AGENCY PREFLIGHT] current turn context"}

    import agency_runtime.core.preflight as preflight_module

    monkeypatch.setattr(preflight_module, "run_preflight", lambda *_a, **_k: _Result())

    projection = _Adapter().build_preflight_context("session", "do the thing", trace_id="turn-2")

    assert "[AGENCY PREFLIGHT] current turn context" in projection["context"]
    assert "[AGENCY SPECIALIST EXPIRY]" in projection["context"]
    assert "database-optimizer" in projection["context"]
