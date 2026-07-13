"""Deterministic delegation evaluation harness.

This suite checks the observable contract for delegation without calling an LLM
or spawning real workers. It is intended for `agency eval delegation` and CI.
"""

from __future__ import annotations

import secrets
import shutil
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from agency_runtime.adapters.claude.wrapper import ClaudeAdapter
from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.generic.wrapper import GenericAdapter
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.delegation.events import record_suggested_delegations
from agency_runtime.core.header.contract import fill_header_fields
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.pipeline import build_routing_context
from agency_runtime.core.store.sqlite import Store


class _SyntheticEvalStore(Store):
    """Store non-sensitive eval evidence without owner-ACL mutation.

    The real Store remains fail-closed. This internal subclass exists only for
    deterministic synthetic records, uses exclusive creation, and retains every
    link/reparse and regular-file check while avoiding a Windows DACL operation
    that restricted agent tokens are not allowed to perform.
    """

    def _ensure_private_storage_file(self) -> None:
        self._assert_storage_paths_safe()
        with self.db_path.open("xb"):
            pass
        self._assert_storage_paths_safe()

    def _repair_storage_permissions(self) -> None:
        self._assert_storage_paths_safe()


@contextmanager
def _temporary_eval_directory() -> Iterator[Path]:
    """Create a synthetic-data temp directory usable by restricted Windows hosts.

    ``tempfile.TemporaryDirectory`` asks Windows for mode ``0o700``. Under a
    restricted Codex token, Python 3.13 can translate that into a DACL that the
    creating process itself cannot traverse. Eval stores contain no credentials
    or user content, so an unpredictable directory with inherited permissions is
    both safe for this purpose and portable across native Windows and POSIX.
    """

    root = Path(tempfile.gettempdir())
    for _attempt in range(100):
        candidate = root / f"agency-delegation-eval-{secrets.token_hex(16)}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        try:
            yield candidate
        finally:
            shutil.rmtree(candidate)
        return
    raise RuntimeError("could not allocate a unique delegation eval directory")


def _header(*, delegated: str = "none") -> str:
    return "\n".join(
        [
            "Agency/Agencies loaded: multi-agent-systems-architect",
            f"Agency/Agencies delegated: {delegated}",
            "Skills loaded: none",
            "Actual Model selected: unknown -> unavailable - no model receipt recorded",
            "Why: eval",
            "How it shaped outcome: eval",
        ]
    )


def _run_case(name: str, fn: Callable[[], dict[str, Any] | None]) -> dict[str, Any]:
    try:
        detail = fn() or {}
        return {"name": name, "passed": True, "detail": detail}
    except AssertionError as exc:
        return {"name": name, "passed": False, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive harness boundary
        return {"name": name, "passed": False, "error": f"{type(exc).__name__}: {exc}"}


def _case_detect_numbered_list() -> dict[str, Any]:
    result = detect_work_units("1. audit delegation layer\n2. add eval coverage")
    assert result["delegate"] is True
    assert result["count"] == 2
    return {"count": result["count"], "source": result["source"]}


def _case_status_query_no_delegate() -> dict[str, Any]:
    result = detect_work_units("what's next")
    assert result["delegate"] is False
    assert result["source"] == "status_query"
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
    assert "[AGENCY PREFLIGHT] No high-confidence specialist match" in context
    assert "[DELEGATION OPPORTUNITY] 2 independent work units" in context
    return {"markers": ["AGENCY PREFLIGHT", "DELEGATION OPPORTUNITY"]}


def _with_store(
    fn: Callable[[Store, HermesAdapter], dict[str, Any] | None],
) -> dict[str, Any] | None:
    with _temporary_eval_directory() as tmpdir:
        store = _SyntheticEvalStore(tmpdir / "agency.db")
        adapter = HermesAdapter(store=store)
        return fn(store, adapter)


def _make_adapter(adapter_cls: type, store: Store):
    if adapter_cls is GenericAdapter:
        return adapter_cls(store=store, cli_cmd="definitely-not-installed")
    return adapter_cls(store=store)


def _case_all_adapters_track_evidence() -> dict[str, Any]:
    hosts: list[str] = []
    for adapter_cls in (
        HermesAdapter,
        OpenClawAdapter,
        CodexAdapter,
        ClaudeAdapter,
        GenericAdapter,
    ):
        with _temporary_eval_directory() as tmpdir:
            store = _SyntheticEvalStore(tmpdir / "agency.db")
            adapter = _make_adapter(adapter_cls, store)
            adapter.post_tool_call_handler(
                tool_name="skill_view",
                args={"name": "agent-reach"},
                session_id="eval-session",
            )
            adapter.post_tool_call_handler(
                tool_name="agency_agents_load",
                args={"agent": "software-architect"},
                session_id="eval-session",
            )
            adapter.post_tool_call_handler(
                tool_name="delegate_task",
                args={"goal": "audit adapter evidence"},
                session_id="eval-session",
            )
            assert adapter.report_skills_loaded("eval-session") == ["agent-reach"]
            assert adapter.report_specialists_loaded("eval-session") == ["software-architect"]
            row = store.get_delegations_for_session("eval-session")[0]
            assert row["host"] == adapter.host_name
            assert row["backend"] == "delegate_task"
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
        with _temporary_eval_directory() as tmpdir:
            store = _SyntheticEvalStore(tmpdir / "agency.db")
            adapter = _make_adapter(adapter_cls, store)
            adapter.post_api_request_handler(
                response={"model": "eval-provider/eval-model"},
                model="task-general",
                session_id="eval-session",
            )
            receipt = store.get_model_receipt_for_session("eval-session")
            assert receipt is not None
            assert receipt["host"] == adapter.host_name
            assert receipt["resolved_provider"] == "eval-provider"
            assert receipt["resolved_model"] == "eval-model"
            hosts.append(adapter.host_name)
    return {"hosts": hosts}


def _case_suggestions_are_persisted() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        del adapter
        count = record_suggested_delegations(
            store,
            session_id="eval-session",
            host="hermes",
            routing={
                "selected_ids": ["multi-agent-systems-architect"],
                "work_units": {
                    "delegate": True,
                    "count": 2,
                    "units": ["audit delegation", "add eval"],
                },
            },
        )
        rows = store.get_delegations_for_session("eval-session")
        assert count == 2
        assert [row["status"] for row in rows] == ["suggested", "suggested"]
        return {"suggested": len(rows)}

    return _with_store(run)


def _case_pre_verify_blocks_open_suggestions() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        store.record_specialist_loaded("eval-session", "multi-agent-systems-architect")
        store.record_delegation(
            trace_id="trace",
            session_id="eval-session",
            host="hermes",
            work_unit_id="unit-1",
            recommended_agent="multi-agent-systems-architect",
            status="suggested",
        )
        result = adapter.pre_verify_handler(
            _header(delegated="none"), session_id="eval-session", attempt=1
        )
        assert result is not None
        assert result["action"] == "continue"
        return {"action": result["action"]}

    return _with_store(run)


def _case_delegate_task_promotes_suggestion() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
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
            args={"goal": "audit delegation"},
            session_id="eval-session",
        )
        rows = store.get_delegations_for_session("eval-session")
        assert rows[0]["status"] == "delegated"
        assert rows[0]["backend"] == "delegate_task"
        fields = fill_header_fields({}, "eval-session", store, "task-chunk-planner")
        assert "delegate_task" in fields["agencies_delegated"]
        return {"header": fields["agencies_delegated"]}

    return _with_store(run)


def _case_agency_agents_delegate_records_event() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        adapter.post_tool_call_handler(
            tool_name="agency_agents_delegate",
            args={"agent": "software-architect", "task": "review design"},
            session_id="eval-session",
        )
        rows = store.get_delegations_for_session("eval-session")
        assert len(rows) == 1
        assert rows[0]["recommended_agent"] == "software-architect"
        assert rows[0]["status"] == "delegated"
        return {"backend": rows[0]["backend"]}

    return _with_store(run)


def _case_skipped_blocker_renders_in_header() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        del adapter
        store.record_delegation(
            trace_id="trace",
            session_id="eval-session",
            host="hermes",
            work_unit_id="unit-1",
            recommended_agent="multi-agent-systems-architect",
            status="skipped",
            skip_reason="delegate_task unavailable",
        )
        fields = fill_header_fields({}, "eval-session", store, "task-chunk-planner")
        assert fields["agencies_delegated"] == "none - delegate_task unavailable"
        return {"header": fields["agencies_delegated"]}

    return _with_store(run)


def _case_recorded_delegation_blocker_is_accepted() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        store.record_specialist_loaded("eval-session", "multi-agent-systems-architect")
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
            _header(delegated="none - agency_agents_delegate unavailable"),
            session_id="eval-session",
            attempt=1,
        )
        assert result is None
        return {"accepted": True}

    return _with_store(run)


def _case_generated_no_delegation_explanation_is_rejected() -> dict[str, Any] | None:
    def run(store: Store, adapter: HermesAdapter) -> dict[str, Any]:
        store.record_specialist_loaded("eval-session", "multi-agent-systems-architect")
        store.record_delegation(
            trace_id="trace",
            session_id="eval-session",
            host="hermes",
            work_unit_id="unit-1",
            recommended_agent="multi-agent-systems-architect",
            status="suggested",
        )
        result = adapter.pre_verify_handler(
            _header(delegated="none - delegation suggested but not executed"),
            session_id="eval-session",
            attempt=1,
        )
        assert result is not None
        assert result["action"] == "continue"
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
