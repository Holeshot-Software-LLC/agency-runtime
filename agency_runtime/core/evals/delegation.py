"""Deterministic delegation evaluation harness.

This suite checks the observable contract for delegation without calling an LLM
or spawning real workers. It is intended for `agency eval delegation` and CI.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agency_runtime.adapters.claude.wrapper import ClaudeAdapter
from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.generic.wrapper import GenericAdapter
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.delegation.events import record_suggested_delegations
from agency_runtime.core.header.contract import fill_header_fields, format_header
from agency_runtime.core.private_paths import private_temporary_directory
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.pipeline import build_routing_context
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


def _case_context_shows_opportunity_without_specialist_match() -> dict[str, Any]:
    context = build_routing_context(
        {
            "selected_ids": [],
            "confidence": 0.0,
            "status": "no_catalog",
            "work_units": {
                "delegate": True,
                "count": 2,
                "confidence": "high",
                "source": "numbered_list",
                "units": ["audit delegation", "add eval"],
            },
        }
    )
    _require(
        "[AGENCY PREFLIGHT] No high-confidence specialist match" in context,
        "no-match context marker is missing",
    )
    _require(
        "[DELEGATION OPPORTUNITY] 2 independent work units" in context,
        "delegation-opportunity context marker is missing",
    )
    return {"markers": ["AGENCY PREFLIGHT", "DELEGATION OPPORTUNITY"]}


def _with_store(
    fn: Callable[[Store, HermesAdapter], dict[str, Any] | None],
) -> dict[str, Any] | None:
    with private_temporary_directory(prefix="delegation-eval") as tmpdir:
        store = Store(tmpdir / "agency.db")
        adapter = HermesAdapter(store=store)
        return fn(store, adapter)


def _make_adapter(adapter_cls: type, store: Store):
    if adapter_cls is GenericAdapter:
        return adapter_cls(store=store, cli_cmd="definitely-not-installed")
    return adapter_cls(store=store)


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
        user_message="synthetic delegation evaluation",
        metadata={
            "source": "delegation-eval",
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
        with private_temporary_directory(prefix="delegation-eval") as tmpdir:
            store = Store(tmpdir / "agency.db")
            adapter = _make_adapter(adapter_cls, store)
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
        with private_temporary_directory(prefix="delegation-eval") as tmpdir:
            store = Store(tmpdir / "agency.db")
            adapter = _make_adapter(adapter_cls, store)
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


def _case_suggestions_are_persisted() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        del adapter
        _create_eval_turn(store)
        count = record_suggested_delegations(
            store,
            session_id="eval-session",
            host="hermes",
            routing={
                "trace_id": "trace",
                "selected_ids": ["multi-agent-systems-architect"],
                "work_units": {
                    "delegate": True,
                    "count": 2,
                    "units": ["audit delegation", "add eval"],
                },
            },
        )
        rows = store.get_delegations("trace")
        _require(count == 2, "suggestion count mismatch")
        _require(
            [row["status"] for row in rows] == ["suggested", "suggested"],
            "suggestion states mismatch",
        )
        return {"suggested": len(rows)}

    return _with_store(run)


def _case_pre_verify_blocks_open_suggestions() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        _create_eval_turn(store)
        store.record_specialist_loaded(
            "eval-session",
            "multi-agent-systems-architect",
            trace_id="trace",
        )
        store.record_delegation(
            trace_id="trace",
            session_id="eval-session",
            host="hermes",
            work_unit_id="unit-1",
            recommended_agent="multi-agent-systems-architect",
            status="suggested",
        )
        result = adapter.pre_verify_handler(
            _header(store, delegated="none"),
            session_id="eval-session",
            attempt=1,
            trace_id="trace",
        )
        _require(result is not None, "open suggestion was accepted")
        _require(result["action"] == "continue", "open suggestion did not continue")
        return {"action": result["action"]}

    return _with_store(run)


def _case_delegate_task_promotes_suggestion() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        _create_eval_turn(store)
        store.record_delegation(
            trace_id="trace",
            session_id="eval-session",
            host="hermes",
            work_unit_id="unit-1",
            recommended_agent="multi-agent-systems-architect",
            status="suggested",
        )
        adapter.post_tool_call_handler(
            tool_name="delegate_task",
            args={
                "agent": "multi-agent-systems-architect",
                "goal": "audit delegation",
                "work_unit_id": "unit-1",
            },
            result={"agent_id": "worker-1", "run_id": "delegate-task:run-1"},
            session_id="eval-session",
            trace_id="trace",
        )
        rows = store.get_delegations("trace")
        _require(rows[0]["status"] == "delegated", "suggestion was not promoted")
        _require(rows[0]["backend"] == "delegate_task", "delegate backend mismatch")
        fields = fill_header_fields({}, "eval-session", store, "task-chunk-planner", "trace")
        _require(
            fields["agencies_delegated"]
            == "none - executed worker has no validated Agency specialist",
            "unvalidated native worker was reported as an Agency specialist",
        )
        return {"header": fields["agencies_delegated"]}

    return _with_store(run)


def _case_agency_agents_delegate_records_event() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        _create_eval_turn(store)
        adapter.post_tool_call_handler(
            tool_name="agency_agents_delegate",
            args={
                "agent": "software-architect",
                "task": "review design",
                "work_unit_id": "unit-design-review",
            },
            result={"agent_id": "worker-2", "run_id": "agency-delegate:run-1"},
            session_id="eval-session",
            trace_id="trace",
        )
        rows = store.get_delegations("trace")
        _require(len(rows) == 1, "public delegation event count mismatch")
        _require(
            rows[0]["recommended_agent"] == "software-architect",
            "public delegation recommendation mismatch",
        )
        _require(rows[0]["status"] == "delegated", "public delegation was not observed")
        return {"backend": rows[0]["backend"]}

    return _with_store(run)


def _case_skipped_blocker_renders_in_header() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        del adapter
        _create_eval_turn(store)
        store.record_delegation(
            trace_id="trace",
            session_id="eval-session",
            host="hermes",
            work_unit_id="unit-1",
            recommended_agent="multi-agent-systems-architect",
            status="skipped",
            skip_reason="delegate_task unavailable",
        )
        fields = fill_header_fields({}, "eval-session", store, "task-chunk-planner", "trace")
        _require(
            fields["agencies_delegated"] == "none - delegate_task unavailable",
            "skipped delegation blocker was not rendered",
        )
        return {"header": fields["agencies_delegated"]}

    return _with_store(run)


def _case_recorded_delegation_blocker_is_accepted() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        _create_eval_turn(store)
        store.record_specialist_loaded(
            "eval-session",
            "multi-agent-systems-architect",
            trace_id="trace",
        )
        store.record_delegation(
            trace_id="trace",
            session_id="eval-session",
            host="hermes",
            work_unit_id="unit-1",
            recommended_agent="multi-agent-systems-architect",
            status="skipped",
            backend="agency_agents_delegate",
            skip_reason="agency_agents_delegate unavailable",
        )
        result = adapter.pre_verify_handler(
            _header(store, delegated="none - agency_agents_delegate unavailable"),
            session_id="eval-session",
            attempt=1,
            trace_id="trace",
        )
        _require(result is None, "recorded delegation blocker was rejected")
        return {"accepted": True}

    return _with_store(run)


def _case_generated_no_delegation_explanation_is_rejected() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        _create_eval_turn(store)
        store.record_specialist_loaded(
            "eval-session",
            "multi-agent-systems-architect",
            trace_id="trace",
        )
        store.record_delegation(
            trace_id="trace",
            session_id="eval-session",
            host="hermes",
            work_unit_id="unit-1",
            recommended_agent="multi-agent-systems-architect",
            status="suggested",
        )
        result = adapter.pre_verify_handler(
            _header(store, delegated="none - delegation suggested but not executed"),
            session_id="eval-session",
            attempt=1,
            trace_id="trace",
        )
        _require(result is not None, "invented delegation explanation was accepted")
        _require(result["action"] == "continue", "invented explanation did not continue")
        return {"action": result["action"]}

    return _with_store(run)


def run_delegation_eval() -> dict[str, Any]:
    """Run the deterministic delegation eval suite."""
    cases = [
        ("detect_numbered_list", _case_detect_numbered_list),
        ("detect_status_query_no_delegate", _case_status_query_no_delegate),
        (
            "context_shows_opportunity_without_specialist_match",
            _case_context_shows_opportunity_without_specialist_match,
        ),
        ("all_adapters_track_evidence", _case_all_adapters_track_evidence),
        ("all_adapters_capture_model_receipts", _case_all_adapters_capture_model_receipts),
        ("suggestions_are_persisted", _case_suggestions_are_persisted),
        ("pre_verify_blocks_open_suggestions", _case_pre_verify_blocks_open_suggestions),
        ("delegate_task_promotes_suggestion", _case_delegate_task_promotes_suggestion),
        ("agency_agents_delegate_records_event", _case_agency_agents_delegate_records_event),
        ("recorded_delegation_blocker_is_accepted", _case_recorded_delegation_blocker_is_accepted),
        ("skipped_blocker_renders_in_header", _case_skipped_blocker_renders_in_header),
        (
            "generated_no_delegation_explanation_is_rejected",
            _case_generated_no_delegation_explanation_is_rejected,
        ),
    ]
    results = [_run_case(name, fn) for name, fn in cases]
    passed = sum(1 for case in results if case["passed"])
    return {
        "suite": "delegation",
        "passed": passed == len(results),
        "passed_count": passed,
        "failed_count": len(results) - passed,
        "cases": results,
    }


__all__ = ["run_delegation_eval"]
