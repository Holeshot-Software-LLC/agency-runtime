"""Rule 4 against the real Store and the real roster -- no stubs.

test_jit_staffing_host_parity.py proves the same wiring against
_JitRosterStore, a hand-built fake with a one-agent roster. That is worth
having, but it cannot catch what the stub happens to get right: handoff §5
records a real bug (_correlation falling back to tool_use_id without validating
the trace via get_run) that "a test stub without get_run will not catch".

So this file runs the whole Agency-side chain for real -- real SQLite Store,
the real bundled roster, real pre_narrow retrieval over it, real prompt
resolution at a pinned version and hash, real specialist-load rows.

It is still not a full end-to-end proof of rule 4. Everything asserted here is
Agency's own self-report; nothing confirms the child actually *received* the
card. That evidence only exists in the host's own on-disk transcript, which no
test in this repo can produce.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.hooks import _JIT_STAFFING_MAX_CARDS, HookBridge
from agency_runtime.core.native_child_prompt_delivery import parse_jit_specialist_delivery
from agency_runtime.core.roster.bundled import bundled_roster
from agency_runtime.core.store.sqlite import Store

SESSION = "rule4-session"
# A plain sentence with no Agency vocabulary in it: the harness spawned this
# child on its own initiative and knows nothing about staffing.
CHILD_TASK = "Review this Python module for security vulnerabilities and unsafe input handling."

# claude/zcode expose the sub-agent tool as "Agent"; codex spawns natively.
_HOST_TOOL = {
    "claude": ("Agent", "prompt"),
    "zcode": ("Agent", "prompt"),
    "codex": ("spawn_agent", "message"),
}


@pytest.fixture(scope="module")
def _seeded_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Seed the real 282-agent roster once; copying it per test is far cheaper."""

    path = tmp_path_factory.mktemp("rule4-seed") / "seed.db"
    store = Store(path)
    for agent in bundled_roster():
        store._activate_prevalidated_agent(agent)
    return path


@pytest.fixture
def store(_seeded_db: Path, tmp_path: Path) -> Store:
    target = tmp_path / "agency.db"
    shutil.copyfile(_seeded_db, target)
    return Store(target)


@pytest.fixture(params=sorted(_HOST_TOOL))
def host(request: pytest.FixtureRequest) -> str:
    return str(request.param)


def _open_turn(store: Store, host: str, trace: str) -> None:
    store.create_run(
        session_id=SESSION,
        trace_id=trace,
        host=host,
        user_message="Audit the request handler.",
    )


def _spawn_payload(host: str, trace: str, task: str = CHILD_TASK) -> dict[str, Any]:
    tool_name, field = _HOST_TOOL[host]
    return {
        "hook_event_name": "PreToolUse",
        "session_id": SESSION,
        "turn_id": trace,
        "tool_name": tool_name,
        "tool_use_id": "toolu_rule4_0001",
        "tool_input": {field: task, "description": "security review"},
    }


def _staff(store: Store, host: str, trace: str, task: str = CHILD_TASK) -> dict[str, Any]:
    return HookBridge(host, store=store).handle(_spawn_payload(host, trace, task))


def _delivered(result: dict[str, Any], host: str) -> str:
    _tool, field = _HOST_TOOL[host]
    return str(result["hookSpecificOutput"]["updatedInput"][field])


def _loads(store: Store, trace: str) -> list[dict[str, Any]]:
    return [
        row for row in store.get_specialist_load_history(SESSION) if row.get("trace_id") == trace
    ]


def test_a_harness_spawned_child_is_handed_a_real_card(store: Store, host: str) -> None:
    """The launch input comes back rewritten, carrying a parseable v5 envelope."""

    trace = f"rule4-handed-{host}"
    _open_turn(store, host, trace)

    result = _staff(store, host, trace)

    delivered = _delivered(result, host)
    assert result["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert delivered != CHILD_TASK, "the child's launch input was not rewritten"
    assert CHILD_TASK in delivered, "the harness's own task must survive verbatim"

    parsed = parse_jit_specialist_delivery(delivered)
    assert parsed is not None, "the delivered task carried no parseable v5 JIT envelope"
    assert parsed.host == host


def test_the_delivered_card_is_a_real_roster_prompt(store: Store, host: str) -> None:
    """Not a placeholder: the body is what the Store actually holds for that slug."""

    trace = f"rule4-realprompt-{host}"
    _open_turn(store, host, trace)

    delivered = _delivered(_staff(store, host, trace), host)

    loads = _loads(store, trace)
    assert loads, "no specialist load was recorded for the staffed child"
    slug = str(loads[0]["agent_slug"])
    assert slug in {agent["slug"] for agent in bundled_roster()}
    stored = store.get_specialist_prompt(slug)
    assert stored is not None and stored.get("prompt_body")
    assert str(stored["prompt_body"]) in delivered, "the delivered card was not the stored prompt"


def test_the_load_is_recorded_without_a_grant_or_delegation(store: Store, host: str) -> None:
    """Rule 4 staffing writes an audit row and nothing else -- no token, no receipt."""

    trace = f"rule4-nogrant-{host}"
    _open_turn(store, host, trace)

    delivered = _delivered(_staff(store, host, trace), host)

    assert _loads(store, trace)
    assert store.get_delegations(trace) == [], "staffing a child must not write a delegation row"
    assert "activation_token" not in delivered


def test_staffing_stays_within_the_card_budget(store: Store, host: str) -> None:
    trace = f"rule4-budget-{host}"
    _open_turn(store, host, trace)

    _staff(store, host, trace)

    assert 1 <= len(_loads(store, trace)) <= _JIT_STAFFING_MAX_CARDS


def test_staffing_is_idempotent_on_an_already_staffed_task(store: Store, host: str) -> None:
    """A replayed hook must not stack a second envelope onto the same child."""

    trace = f"rule4-idempotent-{host}"
    _open_turn(store, host, trace)
    delivered = _delivered(_staff(store, host, trace), host)

    field = _HOST_TOOL[host][1]
    replay = HookBridge(host, store=store).handle(
        {**_spawn_payload(host, trace), "tool_input": {field: delivered}}
    )

    if replay.get("hookSpecificOutput"):
        assert _delivered(replay, host) == delivered


def test_an_unroutable_child_runs_unstaffed_rather_than_blocked(store: Store, host: str) -> None:
    """Rule 8: if Agency cannot help it gets out of the way. It never denies."""

    trace = f"rule4-unroutable-{host}"
    _open_turn(store, host, trace)

    result = _staff(store, host, trace, task="zzzz")

    decision = (result.get("hookSpecificOutput") or {}).get("permissionDecision")
    assert decision in (None, "allow"), f"a host-initiated child was blocked: {result}"
    assert "deny" not in str(result).lower()


def test_a_child_on_an_unopened_trace_is_not_staffed_from_another_turn(
    store: Store,
    host: str,
) -> None:
    """The get_run validation that §5 records a stub as unable to catch."""

    opened = f"rule4-scope-{host}"
    _open_turn(store, host, opened)
    unopened = f"rule4-never-opened-{host}"

    result = HookBridge(host, store=store).handle(_spawn_payload(host, unopened))

    assert _loads(store, unopened) == []
    assert "deny" not in str(result).lower()


def _fail_preflight(store: Store, host: str, trace: str) -> None:
    """Leave one run terminal exactly the way a dead provider leaves it."""

    reservation = store.reserve_session_turn(session_id=SESSION, trace_id=trace, host=host)
    assert store.abandon_preflight_reservation(
        session_id=SESSION,
        trace_id=trace,
        reservation_token=reservation["reservation_token"],
        status="preflight_failed",
    )
    assert store.get_run(trace)["status"] == "preflight_failed"


def test_a_child_is_staffed_even_when_the_parent_turn_failed_preflight(
    store: Store,
    host: str,
) -> None:
    """Rules 4 and 8: the parent's inference failing must not disarm the child.

    Observed in production 2026-08-10. An unreachable provider CLI made every
    planner call fail, so every run was written ``preflight_failed``; the parent
    scope resolver accepted only ``active``/``evidence_only``; and every
    harness-spawned child therefore launched unstaffed -- indistinguishable from
    "rule 4 does not work", and the reason it had never once been observed
    working. A child's cards are chosen by ``pre_narrow`` and
    ``enforce_compatible_set``, which are deterministic, local and network-free,
    so a failed planner call is not the child's problem.
    """

    trace = f"rule4-deadparent-{host}"
    _fail_preflight(store, host, trace)

    result = _staff(store, host, trace)

    delivered = _delivered(result, host)
    assert parse_jit_specialist_delivery(delivered) is not None, (
        "a child was left unstaffed because its parent turn failed preflight"
    )
    assert CHILD_TASK in delivered, "the harness's own task must survive verbatim"

    # The audit row is deliberately NOT asserted here, and its absence is correct:
    # the Store refuses to attach new evidence to a terminal turn ("trace_id
    # belongs to a terminal turn"), which is an integrity rule worth keeping, and
    # `_record_jit_specialist_load` is explicitly best-effort -- "the child keeps
    # its specialist". So a degraded parent yields a staffed child with no
    # `specialists_loaded` row.
    #
    # MEASUREMENT TRAP: in this state rule 4 is provable ONLY from the host's own
    # artifacts (`agency evidence children`), never from Agency's rows. Reading
    # the DB here would report "nothing staffed" about a child that was staffed.
    assert _loads(store, trace) == [], (
        "a terminal parent unexpectedly accepted new turn evidence; if this now "
        "passes, the Store invariant changed and the trap note above is stale"
    )


def test_lifecycle_recording_still_requires_a_live_parent(store: Store, host: str) -> None:
    """The relaxation is opt-in, and only just-in-time staffing opts in.

    Writing a lifecycle audit edge against a turn that has already finished would
    be wrong, so the default stays strict. This pins the asymmetry so a later
    tidy-up cannot quietly collapse the two.
    """

    trace = f"rule4-strictdefault-{host}"
    _fail_preflight(store, host, trace)
    bridge = HookBridge(host, store=store)
    payload = _spawn_payload(host, trace)

    _session, strict_trace, _unit = bridge._native_child_parent_scope(payload)
    _session, staffing_trace, _unit = bridge._native_child_parent_scope(
        payload,
        require_live_parent=False,
    )

    assert strict_trace == "", "a terminal parent must not satisfy the strict default"
    assert staffing_trace == trace, "staffing must still resolve its own parent turn"
