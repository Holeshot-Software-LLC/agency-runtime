"""Rules 2 and 3: the chosen cards are dealt into the caller's own turn.

Rule 2 is the product claim -- "load into the caller, don't spawn": the
specialist works in the parent conversation, not in something Agency started.
Rule 3 is that the caller may hold more than one card when the job needs them
and they do not conflict.

Inference alone chooses (ADR-0118), so these tests stub only the choice and
then follow the real path each host uses for an ordinary user turn. The cards
are real roster specialists and their instruction bodies are read back from the
Store rather than asserted as literals, so the test cannot pass by agreeing
with itself. What the host is handed for that same turn must contain the whole
card -- identity and instruction body -- while the caller has still said
nothing, and no child may exist to have received it instead.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.structured_provider import StructuredProviderResult

_MESSAGE = "Review this security patch."

_ONE_CARD = ("code-reviewer",)

# Rule 3's "when the job needs them and they don't conflict": reviewing a
# security patch wants correctness and exploitability read by different
# expertise. One work unit takes exactly one specialist, so more than one card
# means more than one unit of work in the same turn.
_TWO_CARDS = ("code-reviewer", "ai-generated-code-security-auditor")
_TWO_UNITS = (
    ("unit-review", "code-reviewer", "Review the patch for correctness."),
    ("unit-security", "ai-generated-code-security-auditor", "Review the patch for exploitability."),
)

# Every supported host, entered the way an ordinary user turn really enters it.
_HOSTS = ("claude", "codex", "zcode", "hermes", "openclaw")


def _configured_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Store:
    """Configure one provider so selection may run, bound to this store."""

    from tests.runtime_support import write_provider_config

    db_path = tmp_path / "agency.db"
    config_path = tmp_path / "agency.yaml"
    write_provider_config(config_path, db_path=db_path)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    from agency_runtime.core.config import reset_config_cache

    reset_config_cache()
    return Store(db_path)


def _choose(monkeypatch: pytest.MonkeyPatch, slugs: tuple[str, ...]) -> None:
    """Let inference choose exactly these cards, and nothing else."""

    from agency_runtime.core.workforce import inference as workforce_inference
    from tests.runtime_support import stub_inference_invoker

    monkeypatch.setattr(
        workforce_inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(slugs),
    )


def _choose_one_per_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let inference plan two units of work and staff each with its own card.

    The shared one-unit stub cannot express this: a unit takes exactly one
    specialist, so a second card only exists when there is a second unit.
    """

    def _result(value: dict[str, Any]) -> StructuredProviderResult:
        return StructuredProviderResult(
            value=value,
            provider_name="task-agency-router",
            provider_type="litellm",
            transport="",
            requested_model="router-alias",
            model_group="router-alias",
            actual_model="gpt-5.6-mini",
            model_receipt_source="response.body.model",
            latency_ms=17,
        )

    def _invoke(_provider: Any, _prompt: Any, schema: Any, **_kwargs: Any):
        properties = schema.get("properties", {}) if isinstance(schema, Mapping) else {}
        if "approved" in properties:
            return _result({"approved": True, "reason_codes": []})
        if "request_summary" in properties and "units" in properties:
            return _result(
                {
                    "request_summary": "Read this security patch two ways.",
                    "units": [
                        {
                            "unit_id": unit_id,
                            "outcome": outcome,
                            "artifact_kind": "review-report",
                            "domains": ["software-engineering"],
                            "stacks": [],
                            "capability_ids": ["review"],
                            "novel_capability": "",
                            "depends_on": [],
                        }
                        for unit_id, _slug, outcome in _TWO_UNITS
                    ],
                }
            )
        return _result(
            {
                "units": [
                    {
                        "unit_id": unit_id,
                        "decision": "staff",
                        "ranked_semantic": [
                            {
                                "agent_id": slug,
                                "score": 0.99,
                                "classification": "required",
                                "positive_evidence": ["scope-match"],
                                "negative_evidence": [],
                            }
                        ],
                    }
                    for unit_id, slug, _outcome in _TWO_UNITS
                ]
            }
        )

    from agency_runtime.core.workforce import inference as workforce_inference

    monkeypatch.setattr(workforce_inference, "invoke_structured_provider_result", _invoke)


def _instruction_bodies(store: Store, slugs: tuple[str, ...]) -> dict[str, str]:
    """Read each card's real instruction body straight out of the roster."""

    bodies: dict[str, str] = {}
    for slug in slugs:
        prompt = store.get_specialist_prompt(slug)
        assert prompt, f"{slug} is not in the roster this test relies on"
        body = str(prompt.get("prompt_body") or "").strip()
        assert body, f"{slug} carries no instruction body"
        bodies[slug] = body
    return bodies


def _deal_to_caller(
    host: str,
    store: Store,
    *,
    session_id: str,
    trace_id: str,
) -> str:
    """Return what the host is handed for the caller's own turn."""

    if host in {"claude", "codex", "zcode"}:
        result = HookBridge(host, store=store).handle(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": session_id,
                "turn_id": trace_id,
                "prompt": _MESSAGE,
            }
        )
        output = result.get("hookSpecificOutput") or {}
        return str(output.get("additionalContext") or "")

    adapter_type: Any = HermesAdapter if host == "hermes" else OpenClawAdapter
    projection = adapter_type(store=store).pre_llm_call_handler(
        session_id,
        _MESSAGE,
        trace_id=trace_id,
    )
    return str((projection or {}).get("context") or "")


@pytest.mark.parametrize("host", _HOSTS)
def test_one_chosen_card_is_dealt_into_the_callers_own_turn(
    host: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule 2 on every host: the caller itself receives the whole card."""

    store = _configured_store(tmp_path, monkeypatch)
    _choose(monkeypatch, _ONE_CARD)
    session_id = f"{host}-r2-session"
    trace_id = f"{host}-r2-turn"

    context = _deal_to_caller(host, store, session_id=session_id, trace_id=trace_id)

    bodies = _instruction_bodies(store, _ONE_CARD)
    assert "code-reviewer" in context, context
    # The body is the card. A slug alone is a label for something undelivered.
    assert bodies["code-reviewer"] in context, context
    assert store.get_specialists_for_trace(session_id, trace_id) == ["code-reviewer"]
    # Rule 2 is "load into the caller, don't spawn": the card reached the
    # conversation that was already running, and there is no child that could
    # have received it instead.
    assert store.get_delegations(trace_id) == []


@pytest.mark.parametrize("host", _HOSTS)
def test_several_compatible_cards_are_dealt_into_the_callers_own_turn(
    host: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule 3 on every host: the caller may hold more than one card at once."""

    store = _configured_store(tmp_path, monkeypatch)
    _choose_one_per_unit(monkeypatch)
    session_id = f"{host}-r3-session"
    trace_id = f"{host}-r3-turn"

    context = _deal_to_caller(host, store, session_id=session_id, trace_id=trace_id)

    bodies = _instruction_bodies(store, _TWO_CARDS)
    for slug in _TWO_CARDS:
        assert slug in context, context
        # Whole blocks only: a half-delivered card is not a card.
        assert bodies[slug] in context, context
    assert sorted(store.get_specialists_for_trace(session_id, trace_id)) == sorted(_TWO_CARDS)
    assert store.get_delegations(trace_id) == []
