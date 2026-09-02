"""AR-356: fail-open turns disclose their staffing failure inside the capsule.

A fail-open turn used to deliver the steward kernel and nothing else, so the
parent model could not know it was unstaffed. These tests pin the disclosure
contract (wording hash, bounds, content-free reason classes), prove the line
reaches every host's capsule together with the operator policy, prove staffed
turns are untouched, and cover the tool-degradation half of the scope note
(a specialist loaded mid-turn whose required tools this host never proved).
"""

from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.claude.wrapper import ClaudeAdapter
from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core import preflight_recipe
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.fail_open_disclosure import (
    FAIL_OPEN_DISCLOSURE_HASH,
    FAIL_OPEN_DISCLOSURE_MARKER,
    FAIL_OPEN_DISCLOSURE_TEMPLATE,
    FAIL_OPEN_DISCLOSURE_VERSION,
    MAX_DISCLOSED_REASON_CODES,
    MAX_FAIL_OPEN_DISCLOSURE_CHARS,
    TOOL_DEGRADATION_HASH,
    TOOL_DEGRADATION_MARKER,
    disclosed_reason_class,
    render_fail_open_disclosure,
    render_tool_degradation,
)
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.operator_policy import OPERATOR_POLICY_HEADER
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.preflight_failure import PREFLIGHT_FAILURE_REASONS
from agency_runtime.core.resident_managers import (
    RESIDENT_MANAGER_KERNEL,
    RESIDENT_MANAGER_KERNEL_HASH,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server import mcp_tools

SUBSTANTIVE_REQUEST = (
    "Investigate this unusual request thoroughly and produce a durable implementation."
)
POLICY = "Prefer small reviewable changes.\nAlways cite the receipt id."

HOST_ADAPTERS = (
    ("codex", CodexAdapter),
    ("claude", ClaudeAdapter),
    ("hermes", HermesAdapter),
    ("openclaw", OpenClawAdapter),
)


# --- contract pins ---------------------------------------------------------


def test_disclosure_wording_is_a_versioned_hash_pinned_contract() -> None:
    # Changing either template is a deliberate act: re-pin the hash here and
    # record the new wording in the AR-356 issue document.
    assert FAIL_OPEN_DISCLOSURE_VERSION == 1
    assert (
        FAIL_OPEN_DISCLOSURE_HASH
        == "4324a6b2256fec064faa1c25757445a65c52210ce9db5080a9c82b2b67000f20"
    )
    assert (
        TOOL_DEGRADATION_HASH == "8be24b8ab62b8d376b93675179fe120ad9a0832220032590da2803078be918ce"
    )
    assert FAIL_OPEN_DISCLOSURE_TEMPLATE.startswith(FAIL_OPEN_DISCLOSURE_MARKER)
    assert (
        hashlib.sha256(FAIL_OPEN_DISCLOSURE_TEMPLATE.encode("utf-8")).hexdigest()
        == FAIL_OPEN_DISCLOSURE_HASH
    )


def test_worst_case_disclosure_stays_inside_its_budget_on_one_line() -> None:
    longest_reason = max(PREFLIGHT_FAILURE_REASONS, key=len)
    codes = ["a" + "_b" * 47] * MAX_DISCLOSED_REASON_CODES  # 95-char tokens
    rendered = render_fail_open_disclosure(longest_reason, codes)

    assert len(rendered) <= MAX_FAIL_OPEN_DISCLOSURE_CHARS
    assert "\n" not in rendered
    assert rendered.startswith(FAIL_OPEN_DISCLOSURE_MARKER)


@pytest.mark.parametrize(
    ("reason_code", "staffing_codes", "expected"),
    (
        (
            "workforce_inference_failed",
            ["staffing_critic_rejected"],
            ("workforce_inference_failed; staffing: staffing_critic_rejected"),
        ),
        ("substantive_specialist_unavailable", [], "substantive_specialist_unavailable"),
        # A malformed or unknown reason can never leak into the capsule.
        ("Timeout at https://provider.example/v1", [], "preflight_failed"),
        ("", None, "preflight_failed"),
        (
            "workforce_inference_failed",
            [
                "Inference_Invalid",
                "inference_invalid",
                "provider said: 500 Internal Server Error",
                "selection_confidence_too_low",
                "staffing_critic_rejected",
                "recruiter_abstained",
                "one_code_too_many",
            ],
            (
                "workforce_inference_failed; staffing: inference_invalid, "
                "selection_confidence_too_low, staffing_critic_rejected, recruiter_abstained"
            ),
        ),
    ),
)
def test_reason_class_is_allowlisted_deduplicated_and_bounded(
    reason_code: str,
    staffing_codes: list[str] | None,
    expected: str,
) -> None:
    assert disclosed_reason_class(reason_code, staffing_codes or ()) == expected


def test_tool_degradation_renders_only_for_unproven_required_tools() -> None:
    assert render_tool_degradation("reviewer", [], proven_capabilities=None) == ""
    assert (
        render_tool_degradation(
            "reviewer",
            ["repository-read"],
            proven_capabilities=["repository-read", "shell-execution"],
        )
        == ""
    )

    unproven = render_tool_degradation("reviewer", ["repository-read"], proven_capabilities=None)
    assert unproven.startswith(TOOL_DEGRADATION_MARKER)
    assert "'reviewer' requires repository-read" in unproven
    assert "has not proven any tool availability" in unproven

    partial = render_tool_degradation(
        "reviewer",
        ["repository-read", "browser-automation", "not a label!"],
        proven_capabilities=["repository-read"],
    )
    assert partial.startswith(TOOL_DEGRADATION_MARKER)
    assert "requires browser-automation," in partial
    assert "repository-read" not in partial.split("]")[0].split("requires ")[1]
    assert "not a label" not in partial


# --- capsule delivery ------------------------------------------------------


@pytest.mark.parametrize(("host", "adapter_type"), HOST_ADAPTERS)
def test_fail_open_capsule_discloses_the_staffing_failure_on_every_host(
    tmp_path: Path,
    host: str,
    adapter_type: type[Any],
) -> None:
    store = Store(tmp_path / f"{host}.db")
    adapter = adapter_type(store=store)
    trace_id = f"{host}-fail-open-turn"

    result = adapter.build_preflight_context(
        f"{host}-session",
        SUBSTANTIVE_REQUEST,
        trace_id=trace_id,
    )

    assert isinstance(result, dict)
    assert result["selected_specialists"] == []
    assert result["routing"]["status"] == "no_specialist_fail_open"
    context = str(result["context"])
    assert context.startswith(RESIDENT_MANAGER_KERNEL)
    # The disclosure closes the capsule and names the persisted reason class.
    receipt = store.get_preflight_failure_receipt(f"{host}-session", trace_id)
    assert receipt is not None
    disclosure = render_fail_open_disclosure(
        receipt["reason_code"],
        receipt["staffing_reason_codes"],
    )
    assert context.endswith(disclosure)
    assert context.count(FAIL_OPEN_DISCLOSURE_MARKER) == 1
    assert receipt["reason_code"] in disclosure
    for code in receipt["staffing_reason_codes"][:MAX_DISCLOSED_REASON_CODES]:
        assert code in disclosure


def test_fail_open_capsule_keeps_the_operator_policy_after_agencys_frame(
    tmp_path: Path,
) -> None:
    # The roadmap record claimed fail-open turns already carried the operator
    # policy; they did not (the policy was rendered only on the staffed path).
    store = Store(tmp_path / "policy.db")
    config = dataclasses.replace(AgencyConfig(), operator_policy=POLICY)

    result = HermesAdapter(store=store).build_preflight_context(
        "policy-session",
        SUBSTANTIVE_REQUEST,
        trace_id="policy-fail-open-turn",
        config=config,
    )

    assert result is not None
    context = str(result["context"])
    assert POLICY in context
    kernel_at = context.index(RESIDENT_MANAGER_KERNEL)
    policy_at = context.index(OPERATOR_POLICY_HEADER)
    disclosure_at = context.index(FAIL_OPEN_DISCLOSURE_MARKER)
    assert kernel_at < policy_at < disclosure_at


def test_workforce_inference_failure_discloses_its_staffing_codes_without_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.selector import pipeline

    store = Store(tmp_path / "inference.db")
    provider_detail = "provider stack trace must never reach the model"

    def failed_inference(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "selected_ids": [],
            "status": "inference_invalid",
            "source": "workforce_inference_failure",
            "error": provider_detail,
            "inference_failures": [provider_detail],
            "workforce_staffing": {
                "status": "abstained",
                "abstention_reasons": [
                    {"code": "staffing_critic_rejected", "detail": provider_detail},
                    {"code": "selection_confidence_too_low", "detail": provider_detail},
                ],
            },
        }

    monkeypatch.setattr(pipeline, "route", failed_inference)

    result = run_preflight(
        store,
        session_id="session",
        user_message="Audit and harden the runtime.",
        host="codex",
        trace_id="inference-failed",
    )

    assert result.routing["status"] == "no_specialist_fail_open"
    assert result.context.endswith(
        render_fail_open_disclosure(
            "workforce_inference_failed",
            ["staffing_critic_rejected", "selection_confidence_too_low"],
        )
    )
    assert "workforce_inference_failed; staffing: staffing_critic_rejected" in result.context
    assert provider_detail not in result.context


def test_kernel_hash_literal_is_the_one_bound_before_the_disclosure_landed() -> None:
    # Pinned as a literal (the kernel test recomputes it) so a change to the
    # kernel bytes is visible here: this is the v5 hash recorded live in the
    # AR-355 binding receipt on 2026-09-01, before AR-356 landed, and it is
    # unchanged after it.
    assert (
        RESIDENT_MANAGER_KERNEL_HASH
        == "62c94d87e5beb88cecb711fb5a95c7c4eb56feaa17419cf021e3cb68220f5ed6"
    )


def test_staffed_turns_never_carry_the_disclosure() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "staffed.db")
        config = dataclasses.replace(AgencyConfig(), operator_policy=POLICY)
        result = HermesAdapter(store=store).build_preflight_context(
            "staffed-session",
            "agency status",
            config=config,
        )

    assert result is not None
    assert result["routing"]["status"] != "no_specialist_fail_open"
    assert FAIL_OPEN_DISCLOSURE_MARKER not in str(result["context"])
    assert TOOL_DEGRADATION_MARKER not in str(result["context"])
    # Structural guarantee for "byte-identical": the staffed capsule builder
    # never imports the disclosure module, so it cannot render the line.
    assert "fail_open_disclosure" not in Path(preflight_recipe.__file__).read_text("utf-8")


# --- tool degradation on mid-turn loads -----------------------------------


def test_proven_capabilities_come_only_from_a_ready_recipe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.selector import pipeline
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    store = Store(tmp_path / "proven.db")
    store._activate_prevalidated_agent(
        {
            "slug": "proven-reviewer",
            "name": "Proven Reviewer",
            "description": "Reviews with proven repository access.",
            "version": "1.0",
            "prompt_body": "Review the bounded request.",
        }
    )
    receipt = native_adapter_capability_receipt(
        "codex",
        platform="linux",
        session_id="proven-session",
        trace_id="proven-turn",
    )

    def route(
        _session_id: str,
        user_message: str,
        _catalog: list[dict[str, object]] | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        return {
            "trace_id": str(kwargs.get("trace_id") or "proven-turn"),
            "selected_ids": ["proven-reviewer"],
            "confidence": 0.99,
            "status": "applied",
            "source": "test",
            "query_hash": hashlib.sha256(user_message.encode()).hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": detect_work_units(user_message),
            "execution_context": receipt.as_dict(),
        }

    monkeypatch.setattr(pipeline, "route", route)
    assert store.get_turn_proven_capabilities("proven-session", "proven-turn") is None

    run_preflight(
        store,
        session_id="proven-session",
        trace_id="proven-turn",
        user_message="Review this code for correctness",
        host="codex",
        capability_receipt=receipt,
    )

    proven = store.get_turn_proven_capabilities("proven-session", "proven-turn")
    assert proven is not None
    assert "repository-read" in proven
    assert store.get_turn_proven_capabilities("proven-session", "other-turn") is None


class _LoadStore:
    def __init__(
        self,
        *,
        required_tools: list[str] | None,
        proven: list[str] | None,
        expose_readers: bool = True,
    ) -> None:
        self.loaded: list[tuple[str, str, str]] = []
        self._required = required_tools
        self._proven = proven
        if not expose_readers:
            return
        self.get_roster_entry = self._get_roster_entry
        self.get_turn_proven_capabilities = self._get_turn_proven_capabilities

    def get_specialist_prompt(self, slug: str) -> dict[str, Any]:
        return {
            "name": slug.title(),
            "description": "test card",
            "version": "1.0",
            "prompt_hash": "h" * 64,
            "prompt_body": f"You are {slug}.",
            "prompt_truncated": False,
        }

    def _get_roster_entry(self, _slug: str) -> dict[str, Any] | None:
        if self._required is None:
            return None
        return {"required_tools": list(self._required)}

    def _get_turn_proven_capabilities(self, _session: str, _trace: str) -> list[str] | None:
        return None if self._proven is None else list(self._proven)

    def record_specialist_loaded(self, session_id: str, slug: str, *, trace_id: str) -> None:
        self.loaded.append((session_id, slug, trace_id))


def _load(store: Any, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr(mcp_tools, "active_turn_error", lambda *_args: None)
    return mcp_tools._load_specialist(
        {"slug": "browser-tester", "session_id": "load-session", "trace_id": "load-turn"},
        store,
    )


def test_loading_a_card_with_unproven_required_tools_discloses_the_degradation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _LoadStore(required_tools=["browser-automation", "repository-read"], proven=None)

    result = _load(store, monkeypatch)

    assert result["tool_degradation"].startswith(TOOL_DEGRADATION_MARKER)
    assert (
        "'browser-tester' requires browser-automation, repository-read"
        in (result["tool_degradation"])
    )
    assert result["prompt"].startswith("You are browser-tester.")
    assert result["prompt"].endswith(result["tool_degradation"])
    assert store.loaded == [("load-session", "browser-tester", "load-turn")]


def test_loading_a_card_missing_one_proven_tool_names_only_the_missing_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _LoadStore(
        required_tools=["browser-automation", "repository-read"],
        proven=["repository-read", "shell-execution"],
    )

    result = _load(store, monkeypatch)

    assert "requires browser-automation," in result["tool_degradation"]
    assert "repository-read" not in result["tool_degradation"].split("]")[0]
    assert result["prompt"].endswith(result["tool_degradation"])


@pytest.mark.parametrize(
    "store",
    (
        _LoadStore(required_tools=[], proven=None),
        _LoadStore(required_tools=["repository-read"], proven=["repository-read"]),
        _LoadStore(required_tools=None, proven=None),
        _LoadStore(required_tools=["repository-read"], proven=None, expose_readers=False),
    ),
    ids=("no-required-tools", "all-proven", "no-roster-entry", "store-without-readers"),
)
def test_ordinary_loads_are_byte_identical(
    store: _LoadStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _load(store, monkeypatch)

    assert result["tool_degradation"] == ""
    assert result["prompt"] == "You are browser-tester."
    assert TOOL_DEGRADATION_MARKER not in result["prompt"]
