"""Deterministic host-parity evaluation harness.

Rule 9 says a capability that exists on one host and not another is incomplete.
This suite proves the observable contract holds identically on all five adapters
without calling an LLM: each records the skills and specialists a turn loaded,
each records a delegation the *host itself* chose to make, and each captures a
model receipt. It never spawns a worker — Agency does not decide to spawn.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from agency_runtime.adapters.claude.wrapper import ClaudeAdapter
from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.generic.wrapper import GenericAdapter
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.header.contract import fill_header_fields, format_header
from agency_runtime.core.private_paths import private_temporary_directory
from agency_runtime.core.runtime_control import set_master_enabled
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.store.sqlite import Store


def _header(store: Store, *, delegated: str | None = None) -> str:
    fields = fill_header_fields(
        {},
        "eval-session",
        store,
        "",
        "trace",
    )
    if delegated is not None:
        fields["agencies_delegated"] = delegated
    return format_header(fields)


def _run_case(name: str, fn: Callable[[], dict[str, Any] | None]) -> dict[str, Any]:
    try:
        detail = fn() or {}
        return {"name": name, "passed": True, "detail": detail}
    except AssertionError as exc:
        return {"name": name, "passed": False, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive harness boundary
        return {"name": name, "passed": False, "error": f"{type(exc).__name__}: {exc}"}


def _require(condition: object, message: str) -> None:
    """Fail one deterministic eval independently of Python optimization flags."""

    if not condition:
        raise AssertionError(message)


def _case_detect_numbered_list() -> dict[str, Any]:
    result = detect_work_units("1. audit delegation layer\n2. add eval coverage")
    _require(result["delegate"] is True, "numbered list was not delegated")
    _require(result["count"] == 2, "numbered list did not produce two work units")
    return {"count": result["count"], "source": result["source"]}


def _case_status_query_no_delegate() -> dict[str, Any]:
    result = detect_work_units("what's next")
    _require(result["delegate"] is False, "status query was delegated")
    _require(result["source"] == "status_query", "status-query source was not preserved")
    return {"source": result["source"]}


def _with_store(
    fn: Callable[[Store, HermesAdapter], dict[str, Any] | None],
) -> dict[str, Any] | None:
    with private_temporary_directory(prefix="host-parity-eval") as tmpdir:
        store = Store(tmpdir / "agency.db")
        adapter = HermesAdapter(store=store)
        return fn(store, adapter)


def _make_adapter(adapter_cls: type, store: Store, control_home: Path | None = None):
    """Build one adapter, bound to a master switch this evaluation owns.

    Without `control_home` the adapter reads the operator's durable switch, so
    the result of a supposedly deterministic evaluation changes when someone
    runs `agency off`, and it changes into a misleading evidence mismatch
    rather than a statement that Agency was disabled.  Callers inside the eval
    always pass a private root.
    """

    if adapter_cls is GenericAdapter:
        adapter = adapter_cls(store=store, cli_cmd="definitely-not-installed")
    else:
        adapter = adapter_cls(store=store)
    if control_home is not None:
        set_master_enabled(True, home_dir=control_home)
        adapter.enforcement_control_home = control_home
        _require(
            adapter.runtime_enabled(),
            f"{adapter.host_name} eval could not enable its private master switch",
        )
    return adapter


def _create_eval_turn(
    store: Store,
    *,
    trace_id: str = "trace",
    host: str = "hermes",
) -> None:
    """Create the authoritative turn parent used by synthetic eval evidence."""
    store.create_run(
        trace_id=trace_id,
        session_id="eval-session",
        host=host,
        user_message="synthetic host-parity evaluation",
        metadata={
            "source": "host-parity-eval",
            "request_kind": "nontrivial",
        },
    )


def _case_all_adapters_track_evidence() -> dict[str, Any]:
    hosts: list[str] = []
    for adapter_cls in (
        HermesAdapter,
        OpenClawAdapter,
        CodexAdapter,
        ClaudeAdapter,
        GenericAdapter,
    ):
        with private_temporary_directory(prefix="host-parity-eval") as tmpdir:
            store = Store(tmpdir / "agency.db")
            adapter = _make_adapter(adapter_cls, store, tmpdir / "control-home")
            trace_id = f"eval-{adapter.host_name}"
            _create_eval_turn(store, trace_id=trace_id, host=adapter.host_name)
            adapter.post_tool_call_handler(
                tool_name="skill_view",
                args={"name": "agent-reach"},
                session_id="eval-session",
                trace_id=trace_id,
            )
            adapter.post_tool_call_handler(
                tool_name="agency_agents_load",
                args={"agent": "software-architect"},
                session_id="eval-session",
                trace_id=trace_id,
            )
            adapter.post_tool_call_handler(
                tool_name="delegate_task",
                args={
                    "agent": "software-architect",
                    "goal": "audit adapter evidence",
                    "work_unit_id": "unit-adapter-audit",
                },
                result={
                    "agent_id": f"eval-worker-{adapter.host_name}",
                    "native_run_id": f"eval-run-{adapter.host_name}",
                    "status": "completed",
                },
                session_id="eval-session",
                trace_id=trace_id,
            )
            _require(
                store.get_skills_for_trace("eval-session", trace_id) == ["agent-reach"],
                f"{adapter.host_name} skill evidence mismatch",
            )
            _require(
                store.get_specialists_for_trace("eval-session", trace_id) == ["software-architect"],
                f"{adapter.host_name} specialist evidence mismatch",
            )
            row = store.get_delegations(trace_id)[0]
            _require(row["host"] == adapter.host_name, "delegation host mismatch")
            _require(row["backend"] == "delegate_task", "delegation backend mismatch")
            hosts.append(adapter.host_name)
    return {"hosts": hosts}


def _case_all_adapters_capture_model_receipts() -> dict[str, Any]:
    hosts: list[str] = []
    for adapter_cls in (
        HermesAdapter,
        OpenClawAdapter,
        CodexAdapter,
        ClaudeAdapter,
        GenericAdapter,
    ):
        with private_temporary_directory(prefix="host-parity-eval") as tmpdir:
            store = Store(tmpdir / "agency.db")
            adapter = _make_adapter(adapter_cls, store, tmpdir / "control-home")
            trace_id = f"eval-model-{adapter.host_name}"
            _create_eval_turn(store, trace_id=trace_id, host=adapter.host_name)
            adapter.post_api_request_handler(
                response={"model": "eval-provider/eval-model"},
                model="task-general",
                session_id="eval-session",
                trace_id=trace_id,
            )
            receipt = store.get_model_receipt(trace_id)
            if receipt is None:
                raise AssertionError(f"{adapter.host_name} model receipt is missing")
            _require(receipt["host"] == adapter.host_name, "model receipt host mismatch")
            _require(
                receipt["resolved_provider"] == "eval-provider",
                "model receipt provider mismatch",
            )
            _require(receipt["resolved_model"] == "eval-model", "model receipt mismatch")
            hosts.append(adapter.host_name)
    return {"hosts": hosts}


def _case_cards_expire_with_their_turn() -> dict[str, Any]:
    """Prove rule 7 on every host: a card seen in one turn is absent from the next.

    The card is dealt through the adapter, so each host records it the same way.
    Completing the turn must expire it, and the following turn in the same
    session must start with no specialist at all -- the card returns to the
    cabinet rather than staying with the generalist.
    """

    hosts: list[str] = []
    for adapter_cls in (
        HermesAdapter,
        OpenClawAdapter,
        CodexAdapter,
        ClaudeAdapter,
        GenericAdapter,
    ):
        with private_temporary_directory(prefix="host-parity-eval") as tmpdir:
            store = Store(tmpdir / "agency.db")
            adapter = _make_adapter(adapter_cls, store, tmpdir / "control-home")
            first = f"eval-expiry-first-{adapter.host_name}"
            second = f"eval-expiry-second-{adapter.host_name}"

            _create_eval_turn(store, trace_id=first, host=adapter.host_name)
            adapter.post_tool_call_handler(
                tool_name="agency_agents_load",
                args={"agent": "software-architect"},
                session_id="eval-session",
                trace_id=first,
            )
            _require(
                store.get_specialists_for_trace("eval-session", first) == ["software-architect"],
                f"{adapter.host_name} card missing from the turn that loaded it",
            )

            # A run is closed by its own identity, which is not the trace id;
            # passing the trace would silently close nothing.
            store.complete_run(str(store.get_run(first)["id"]))
            _create_eval_turn(store, trace_id=second, host=adapter.host_name)

            # Per-turn evidence is immutable, so the loading turn keeps its row
            # forever.  Rule 7 is about the *next* turn: the card must not be
            # held there, and its expiry must be stated, because a card already
            # appended to the caller's context cannot be retracted.
            _require(
                store.get_specialists_for_trace("eval-session", first) == ["software-architect"],
                f"{adapter.host_name} rewrote the evidence of the turn that loaded the card",
            )
            _require(
                store.get_specialists_for_trace("eval-session", second) == [],
                f"{adapter.host_name} card carried into the next turn",
            )

            history = store.get_specialist_load_history("eval-session")
            _require(
                [row["trace_id"] for row in history] == [first],
                f"{adapter.host_name} specialist history is not bound to one turn",
            )
            _require(
                history[0]["expired_at"] is not None,
                f"{adapter.host_name} the card was never marked expired",
            )
            _require(
                "software-architect"
                in store.get_expired_specialists_to_announce("eval-session", second),
                f"{adapter.host_name} expiry was never stated on the following turn",
            )
            hosts.append(adapter.host_name)
    return {"hosts": hosts}


def run_host_parity_eval() -> dict[str, Any]:
    """Run the deterministic host-parity eval suite."""
    cases = [
        ("detect_numbered_list", _case_detect_numbered_list),
        ("detect_status_query_no_delegate", _case_status_query_no_delegate),
        ("all_adapters_track_evidence", _case_all_adapters_track_evidence),
        ("all_adapters_capture_model_receipts", _case_all_adapters_capture_model_receipts),
        ("cards_expire_with_their_turn", _case_cards_expire_with_their_turn),
    ]
    results = [_run_case(name, fn) for name, fn in cases]
    passed = sum(1 for case in results if case["passed"])
    return {
        "suite": "host-parity",
        "passed": passed == len(results),
        "passed_count": passed,
        "failed_count": len(results) - passed,
        "cases": results,
    }


__all__ = ["run_host_parity_eval"]
