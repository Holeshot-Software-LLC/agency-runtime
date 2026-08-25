"""Uniform completion-policy regressions for public and Hermes boundaries."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from agency_runtime.adapters.hermes import bridge as hermes_bridge
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.core.header.contract import finalize_header
from agency_runtime.core.header.finalize import finalize_response, response_hash
from agency_runtime.core.installer import install_agent_adapter
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.mcp_tools import dispatch_tool_call
from tests.runtime_support import ensure_private_test_directory

pytestmark = pytest.mark.usefixtures("private_installer_launcher")


def _create_turn(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
    request_kind: str,
    host: str = "hermes",
) -> None:
    store.create_run(
        trace_id=trace_id,
        session_id=session_id,
        host=host,
        metadata={"request_kind": request_kind},
    )


def _suggest_delegation(store: Store, *, session_id: str, trace_id: str) -> None:
    store.record_delegation(
        trace_id=trace_id,
        session_id=session_id,
        host="hermes",
        work_unit_id="unit-review",
        recommended_agent="code-reviewer",
        status="suggested",
        backend="",
    )


def _load_generated_hermes(tmp_path: Path) -> ModuleType:
    ensure_private_test_directory(tmp_path / ".hermes" / "plugins", parents=True)
    result = install_agent_adapter("hermes", home_dir=tmp_path)
    assert result["ok"] is True
    plugin_path = Path(result["plugin_path"])
    module_name = f"agency_runtime_generated_hermes_{tmp_path.name}"
    spec = importlib.util.spec_from_file_location(module_name, plugin_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._adapter = None

    def invoke(action: str, payload: dict[str, object] | None = None) -> object:
        if module._adapter is None:
            raise RuntimeError("test adapter unavailable")
        return hermes_bridge.handle(
            {"action": action, **dict(payload or {})},
            adapter=module._adapter,
        )

    module._invoke = invoke
    module._terminalize_policy_rejection = hermes_bridge._terminalize_policy_rejection
    return module


def test_hermes_accepts_exact_first_visible_response_constructed_by_finalize_tool(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "hermes-first-pass.db")
    _create_turn(
        store,
        session_id="hermes-session",
        trace_id="hermes-turn",
        request_kind="trivial",
    )

    finalized = dispatch_tool_call(
        "agency.finalize",
        {
            "draft_text": "First visible response.",
            "session_id": "hermes-session",
            "trace_id": "hermes-turn",
        },
        store,
    )

    assert finalized["action"] == "accept"
    assert (
        hermes_bridge.handle(
            {
                "action": "transform_llm_output",
                "session_id": "hermes-session",
                "trace_id": "hermes-turn",
                "response_text": finalized["text"],
            },
            adapter=HermesAdapter(store),
        )
        == finalized["text"]
    )
    assert store.get_run("hermes-turn")["status"] == "completed"


def test_generated_hermes_registers_callable_first_pass_finalizer(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "hermes-native-finalizer.db")
    _create_turn(
        store,
        session_id="hermes-session",
        trace_id="hermes-turn",
        request_kind="trivial",
    )
    module = _load_generated_hermes(tmp_path)
    adapter = HermesAdapter(store)
    module._adapter = adapter
    assert module._MAX_FINALIZER_RESULT_CHARS == hermes_bridge.MAX_FINALIZER_RESULT_CHARS
    module._remember_turn("hermes-session", "hermes-turn")
    initial_snapshot = hermes_bridge._header_snapshot_context(
        adapter,
        session_id="hermes-session",
        trace_id="hermes-turn",
        model="task-general",
    )
    assert "Skills loaded: none" in initial_snapshot
    assert "Actual Model selected: requested execution alias: task-general" in initial_snapshot

    store.record_skill_loaded(
        "hermes-session",
        "current-evidence-skill",
        trace_id="hermes-turn",
    )
    adapter.post_api_request_handler(
        response={"model": "local/current-model"},
        model="task-general",
        session_id="hermes-session",
        trace_id="hermes-turn",
    )

    class ToolContext:
        def __init__(self) -> None:
            self.tools: dict[str, dict[str, Any]] = {}

        def register_hook(self, *_args: object, **_kwargs: object) -> None:
            pass

        def register_command(self, *_args: object, **_kwargs: object) -> None:
            pass

        def register_tool(self, **kwargs: Any) -> None:
            self.tools[str(kwargs["name"])] = kwargs

    context = ToolContext()
    module.register(context)

    assert set(context.tools) == {"agency_finalize"}
    registration = context.tools["agency_finalize"]
    assert registration["toolset"] == "agency-runtime"
    assert registration["schema"]["name"] == "agency_finalize"
    assert registration["schema"]["parameters"]["required"] == ["draft_text"]
    assert set(registration["schema"]["parameters"]["properties"]) == {"draft_text"}

    finalized_text = registration["handler"](
        {"draft_text": "First native Hermes response."},
        session_id="hermes-session",
        task_id="hermes-task",
    )

    assert finalized_text.startswith("Agency/Agencies loaded: none\n")
    assert "Skills loaded: current-evidence-skill\n" in finalized_text
    assert (
        "Actual Model selected: observed execution receipt: "
        "[general] task-general -> local/current-model via task-general (host)\n"
    ) in finalized_text
    assert finalized_text.endswith("First native Hermes response.")
    assert store.get_run("hermes-turn")["status"] == "completed"
    assert (
        module._pre_verify(
            finalized_text,
            attempt=0,
            conversation_id="hermes-session",
            turn_id="hermes-turn",
        )
        is None
    )
    assert (
        module._transform_llm_output(
            finalized_text,
            conversation_id="hermes-session",
            turn_id="hermes-turn",
        )
        == finalized_text
    )


def test_generated_hermes_finalizer_rejects_draft_above_inline_transport_budget(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "hermes-native-finalizer-bound.db")
    _create_turn(
        store,
        session_id="hermes-session",
        trace_id="hermes-turn",
        request_kind="trivial",
    )
    module = _load_generated_hermes(tmp_path)
    module._adapter = HermesAdapter(store)
    module._remember_turn("hermes-session", "hermes-turn")
    draft = "🔥" * (hermes_bridge.MAX_FINALIZER_DRAFT_CHARS + 1)

    result = json.loads(
        module._agency_finalize(
            {"draft_text": draft},
            session_id="hermes-session",
            task_id="hermes-task",
        )
    )

    assert result == {
        "action": "continue",
        "text": "",
        "missing": ["host_transport"],
    }
    assert store.get_run("hermes-turn")["status"] == "active"
    assert store.get_authoritative_finalization("hermes-session", "hermes-turn") is None


def test_hermes_bridge_refuses_accepted_text_above_inline_transport_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "hermes-native-finalizer-transport.db")
    _create_turn(
        store,
        session_id="hermes-session",
        trace_id="hermes-turn",
        request_kind="trivial",
    )
    monkeypatch.setattr(hermes_bridge, "MAX_FINALIZER_RESULT_CHARS", 64)

    result = hermes_bridge.handle(
        {
            "action": "finalize",
            "session_id": "hermes-session",
            "trace_id": "hermes-turn",
            "draft_text": "This draft fits the plugin input but its header cannot stay inline.",
        },
        adapter=HermesAdapter(store),
    )

    assert result == {
        "action": "continue",
        "text": "",
        "missing": ["host_transport"],
    }
    assert store.get_run("hermes-turn")["status"] == "active"
    assert store.get_authoritative_finalization("hermes-session", "hermes-turn") is None


def test_generated_hermes_finalizer_rejects_missing_native_correlation(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "hermes-native-finalizer-correlation.db")
    _create_turn(
        store,
        session_id="hermes-session",
        trace_id="hermes-turn",
        request_kind="trivial",
    )
    module = _load_generated_hermes(tmp_path)
    module._adapter = HermesAdapter(store)
    result = json.loads(
        module._agency_finalize(
            {"draft_text": "Do not finalize this uncorrelated turn."},
        )
    )

    assert result == {
        "action": "continue",
        "text": "",
        "missing": ["correlation"],
    }
    assert store.get_run("hermes-turn")["status"] == "active"
    assert store.get_authoritative_finalization("hermes-session", "hermes-turn") is None


def test_hermes_transform_rejects_unfinalized_natural_response_without_repair(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "hermes-unfinalized.db")
    _create_turn(
        store,
        session_id="hermes-session",
        trace_id="hermes-turn",
        request_kind="trivial",
    )

    transformed = hermes_bridge.handle(
        {
            "action": "transform_llm_output",
            "session_id": "hermes-session",
            "trace_id": "hermes-turn",
            "response_text": "Natural response without the Agency header.",
        },
        adapter=HermesAdapter(store),
    )

    assert transformed == hermes_bridge.FINALIZATION_BLOCK_RESPONSE
    assert "Natural response" not in transformed
    assert store.get_run("hermes-turn")["status"] == "response_invalid"


def test_public_finalizer_rejects_evidence_revision_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "public-race.db")
    _create_turn(
        store,
        session_id="public-session",
        trace_id="public-turn",
        request_kind="trivial",
        host="mcp",
    )
    commit = store.commit_terminal_finalization

    def race_commit(**kwargs: object) -> dict[str, object]:
        store.record_skill_loaded(
            "public-session",
            "late-skill",
            trace_id="public-turn",
        )
        return commit(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(store, "commit_terminal_finalization", race_commit)

    result = finalize_response(
        "Substantive answer.",
        trace_metadata={
            "session_id": "public-session",
            "trace_id": "public-turn",
            "host": "mcp",
        },
        store=store,
    )

    assert result["action"] == "continue"
    assert result["missing"] == ["evidence_changed"]
    assert store.get_run("public-turn")["status"] == "active"
    assert store.get_skills_for_trace("public-session", "public-turn") == ["late-skill"]
    assert store.get_authoritative_finalization("public-session", "public-turn") is None


def test_generated_hermes_output_hook_rejects_missing_correlation(tmp_path: Path) -> None:
    module = _load_generated_hermes(tmp_path)
    module._adapter = HermesAdapter(store=Store(tmp_path / "missing.db"))
    original = "Sensitive unverified draft."

    replacement = module._transform_llm_output(original)

    assert replacement == module._FINALIZATION_BLOCK_RESPONSE
    assert replacement != original
    assert original not in replacement
    assert 0 < len(replacement) <= 512


def test_generated_hermes_output_hook_rejects_ambiguous_correlation(tmp_path: Path) -> None:
    store = Store(tmp_path / "ambiguous.db")
    _create_turn(store, session_id="session", trace_id="turn-a", request_kind="trivial")
    _create_turn(store, session_id="session", trace_id="turn-b", request_kind="trivial")
    module = _load_generated_hermes(tmp_path)
    module._adapter = HermesAdapter(store=store)

    original = "Ambiguously correlated draft."
    replacement = module._transform_llm_output(original, conversation_id="session")

    assert replacement == module._FINALIZATION_BLOCK_RESPONSE
    assert replacement != original
    assert store.get_run("turn-a")["status"] == "active"
    assert store.get_run("turn-b")["status"] == "active"


def test_generated_hermes_output_hook_rejects_store_persistence_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "failure.db")
    _create_turn(store, session_id="session", trace_id="turn", request_kind="trivial")
    module = _load_generated_hermes(tmp_path)
    module._adapter = HermesAdapter(store=store)
    attempts = 0

    def fail_commit(**_kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("storage offline")

    monkeypatch.setattr(store, "commit_terminal_finalization", fail_commit)

    original = "Draft that must not survive persistence failure."
    replacement = module._transform_llm_output(
        original,
        conversation_id="session",
        turn_id="turn",
    )

    assert replacement == module._FINALIZATION_BLOCK_RESPONSE
    assert replacement != original
    assert original not in replacement
    assert 0 < len(replacement) <= 512
    assert store.get_run("turn")["status"] == "active"
    assert attempts == 1


def test_generated_hermes_output_hook_does_not_terminalize_generic_failure(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "generic-failure.db")
    _create_turn(store, session_id="session", trace_id="turn", request_kind="trivial")
    module = _load_generated_hermes(tmp_path)

    class BrokenAdapter(HermesAdapter):
        def apply_finalization(self, *_args: object, **_kwargs: object) -> str:
            raise RuntimeError("unexpected formatter failure")

    module._adapter = BrokenAdapter(store=store)
    exact = finalize_header(
        "Draft with an exact first-pass header.",
        "session",
        store,
        "",
        "turn",
    )

    replacement = module._transform_llm_output(
        exact,
        conversation_id="session",
        turn_id="turn",
    )

    # Rule 8: finalization raising is Agency being unavailable, not a verdict on
    # the draft, so the host's own text is returned unchanged.  An Agency fault
    # still must not terminalize the turn.
    assert replacement == exact
    assert store.get_run("turn")["status"] == "active"
    assert store.get_authoritative_finalization("session", "turn") is None


def test_generated_hermes_output_hook_rejects_open_delegation(tmp_path: Path) -> None:
    store = Store(tmp_path / "delegation.db")
    _create_turn(store, session_id="session", trace_id="turn", request_kind="nontrivial")
    store.record_specialist_loaded("session", "code-reviewer", trace_id="turn")
    _suggest_delegation(store, session_id="session", trace_id="turn")
    module = _load_generated_hermes(tmp_path)
    module._adapter = HermesAdapter(store=store)

    original = "Draft that ignored an open delegation."
    replacement = module._transform_llm_output(
        original,
        conversation_id="session",
        turn_id="turn",
    )

    assert replacement == module._FINALIZATION_BLOCK_RESPONSE
    assert replacement != original
    assert store.get_run("turn")["status"] == "response_invalid"
    terminal = store.get_authoritative_finalization(
        "session",
        "turn",
        action="response_invalid",
        response_hash=response_hash(module._FINALIZATION_BLOCK_RESPONSE),
    )
    assert terminal is not None

    _create_turn(store, session_id="session", trace_id="next-turn", request_kind="trivial")
    next_exact = finalize_header(
        "The next turn remains independently finalizable.",
        "session",
        store,
        "",
        "next-turn",
    )
    next_response = module._transform_llm_output(
        next_exact,
        conversation_id="session",
    )
    assert next_response.endswith("The next turn remains independently finalizable.")
    assert store.get_run("next-turn")["status"] == "completed"


def test_generated_hermes_pre_verify_fails_first_pass_then_safe_transform(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "pre-verify.db")
    _create_turn(store, session_id="session", trace_id="turn", request_kind="nontrivial")
    store.record_specialist_loaded("session", "code-reviewer", trace_id="turn")
    _suggest_delegation(store, session_id="session", trace_id="turn")
    module = _load_generated_hermes(tmp_path)
    module._adapter = HermesAdapter(store=store)
    native = {"conversation_id": "session", "turn_id": "turn"}

    first = module._pre_verify("Invalid draft.", attempt=0, **native)

    assert first is None
    assert store.get_run("turn")["status"] == "response_invalid"
    assert module._pre_verify("Invalid draft.", attempt=1, **native) is None
    assert module._transform_llm_output("Invalid draft.", **native) == (
        module._FINALIZATION_BLOCK_RESPONSE
    )
    assert (
        store.get_authoritative_finalization(
            "session",
            "turn",
            action="response_invalid",
            response_hash=response_hash(module._FINALIZATION_BLOCK_RESPONSE),
        )
        is not None
    )


def test_generated_hermes_pre_verify_failure_is_bounded_and_fail_closed(
    tmp_path: Path,
) -> None:
    module = _load_generated_hermes(tmp_path)

    class BrokenAdapter:
        def pre_verify_handler(self, **_kwargs: object) -> None:
            raise RuntimeError("secret internal failure")

    module._adapter = BrokenAdapter()

    decision = module._pre_verify("Sensitive draft.", attempt=0)

    assert decision is None


def test_generated_hermes_adapter_construction_failure_returns_the_draft(
    tmp_path: Path,
) -> None:
    """Rule 8: Agency that cannot even construct may not withhold the turn.

    A draft the verifier evaluated and rejected is still replaced elsewhere.
    Here Agency never ran, so it has no finding about the response, and
    withholding a completed turn to report an Agency fault is precisely the
    failure mode the rule exists to prevent.
    """

    module = _load_generated_hermes(tmp_path)
    module._adapter = None

    def fail_adapter() -> None:
        raise RuntimeError("database unavailable")

    module.HermesAdapter = fail_adapter
    original = "Draft written while Agency was unavailable."

    assert module._pre_verify(original, attempt="invalid") is None
    assert module._pre_verify(original, attempt=0) is None
    assert module._transform_llm_output(original) == original


def test_generated_hermes_terminal_receipt_requires_exact_authority(
    tmp_path: Path,
) -> None:
    module = _load_generated_hermes(tmp_path)

    class ReceiptStore:
        def __init__(self) -> None:
            self.missing: list[str] = []

        def commit_terminal_finalization(self, **kwargs: object) -> dict[str, object]:
            self.missing = list(kwargs["missing"])  # type: ignore[arg-type]
            return {
                "authoritative": True,
                "outcome": "committed",
                "action": "accept",
                "response_hash": kwargs["response_hash"],
                "status": "retry_exhausted",
            }

    class ReceiptAdapter:
        store = ReceiptStore()

        @staticmethod
        def resolve_turn_trace(_session_id: str, trace_id: str) -> str:
            return trace_id

        @staticmethod
        def evaluate_completion_policy(
            _response: str,
            **_kwargs: object,
        ) -> dict[str, object]:
            return {
                "action": "continue",
                "evidence_revision": 1,
                "missing": "malformed-not-a-list",
            }

    adapter = ReceiptAdapter()

    assert (
        module._terminalize_policy_rejection(
            adapter,
            "Rejected response.",
            "session",
            "turn",
            "",
        )
        is False
    )
    assert adapter.store.missing == ["completion_policy"]


def test_generated_hermes_output_hook_accepts_only_terminal_accept(tmp_path: Path) -> None:
    store = Store(tmp_path / "success.db")
    _create_turn(store, session_id="session", trace_id="turn", request_kind="trivial")
    module = _load_generated_hermes(tmp_path)
    module._adapter = HermesAdapter(store=store)

    exact = finalize_header(
        "Substantive answer.",
        "session",
        store,
        "",
        "turn",
    )
    response = module._transform_llm_output(
        exact,
        conversation_id="session",
        turn_id="turn",
    )

    assert response.endswith("Substantive answer.")
    assert response == exact
    assert response.startswith("Agency/Agencies loaded: none\n")
    assert store.get_run("turn")["status"] == "completed"
    assert store.get_authoritative_finalization("session", "turn") is not None


def test_hermes_runtime_disabled_remains_intentional_passthrough(tmp_path: Path) -> None:
    store = Store(tmp_path / "disabled.db")
    store.set_host_control("hermes", enabled=False, expected_generation=0, source="test")
    module = _load_generated_hermes(tmp_path)
    module._adapter = HermesAdapter(store=store)
    module._remember_turn("session", "turn")

    assert module._transform_llm_output("Original answer.") == "Original answer."
    assert (
        module._agency_finalize(
            {"draft_text": "Original answer."},
            session_id="session",
        )
        == "Original answer."
    )
    long_draft = "x" * (hermes_bridge.MAX_FINALIZER_DRAFT_CHARS + 1)
    assert (
        module._agency_finalize(
            {"draft_text": long_draft},
            session_id="session",
        )
        == long_draft
    )
    module._forget_turn("session")
    assert (
        module._agency_finalize(
            {"draft_text": long_draft},
            session_id="session",
        )
        == long_draft
    )
