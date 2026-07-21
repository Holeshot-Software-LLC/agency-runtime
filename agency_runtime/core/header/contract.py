"""Agency response header contract.

Every finalized Agency Runtime answer begins with six auditable lines that make
specialist use, delegation, skill context, and actual model selection explicit.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, TypedDict

from agency_runtime.core.header.explanations import (
    humanize_effect_codes,
    humanize_reason_codes,
)
from agency_runtime.core.host_guidance import (
    NATIVE_DELEGATION_GUIDANCE,
    native_delegation_instruction,
    specialist_load_guidance,
)
from agency_runtime.core.resident_manager_binding import (
    canonical_resident_manager_host,
    validate_resident_manager_binding,
)
from agency_runtime.core.resident_managers import (
    RESIDENT_MANAGER_SLUGS,
    is_current_resident_manager_kernel_reference,
)

HEADER_FIELDS: tuple[tuple[str, str], ...] = (
    ("agencies_loaded", "Agency/Agencies loaded"),
    ("agencies_delegated", "Agency/Agencies delegated"),
    ("skills_loaded", "Skills loaded"),
    ("actual_model_selected", "Actual Model selected"),
    ("why", "Why"),
    ("how_it_shaped_outcome", "How it shaped outcome"),
)

_REQUIRED_KEYS = tuple(key for key, _ in HEADER_FIELDS)
_LABEL_TO_KEY = {label.lower(): key for key, label in HEADER_FIELDS}
_KEY_TO_LABEL = dict(HEADER_FIELDS)

_EMPTY_VALUES = {
    "",
    "<none>",
    "<none | agent-id[, agent-id...]>",
    "<none | skill-id[, skill-id...]>",
    "<one line>",
}
_EVIDENCE_CODE = re.compile(r"^[a-z0-9][a-z0-9_.:+-]{0,95}$")
_MAX_HEADER_CODES = 12


class EvidenceCorrelationError(ValueError):
    """Raised when authoritative header evidence cannot identify one turn."""


class CompletionPolicyViolation(TypedDict):
    """Structured reason that one response cannot reach terminal acceptance."""

    message: str
    missing: list[str]


class CompletionPolicyDecision(TypedDict, total=False):
    """Internal accept-or-revise decision bound to one evidence revision."""

    action: str
    message: str
    missing: list[str]
    evidence_revision: int
    delegation_strength: str


def _validate_snapshot_collections(snapshot: Mapping[str, Any]) -> None:
    for key in ("skills", "specialists", "delegations"):
        if not isinstance(snapshot.get(key), list):
            raise EvidenceCorrelationError(f"{key} evidence could not be verified")
    if not all(isinstance(value, str) for value in snapshot["skills"]):
        raise EvidenceCorrelationError("skills evidence could not be verified")
    if not all(isinstance(value, str) for value in snapshot["specialists"]):
        raise EvidenceCorrelationError("specialists evidence could not be verified")
    if not all(isinstance(value, Mapping) for value in snapshot["delegations"]):
        raise EvidenceCorrelationError("delegations evidence could not be verified")
    receipt = snapshot.get("model_receipt")
    if receipt is not None and not isinstance(receipt, Mapping):
        raise EvidenceCorrelationError("model receipt evidence could not be verified")
    resident_managers = snapshot.get("resident_managers", [])
    if not isinstance(resident_managers, list) or not all(
        isinstance(value, str) for value in resident_managers
    ):
        raise EvidenceCorrelationError("resident manager evidence could not be verified")
    resident_kernel = snapshot.get("resident_manager_kernel")
    resident_binding = snapshot.get("resident_manager_binding")
    if resident_binding is not None and not isinstance(resident_binding, Mapping):
        raise EvidenceCorrelationError("resident manager binding could not be verified")
    if resident_managers:
        if tuple(resident_managers) != RESIDENT_MANAGER_SLUGS:
            raise EvidenceCorrelationError("resident manager identity could not be verified")
        if not is_current_resident_manager_kernel_reference(resident_kernel):
            raise EvidenceCorrelationError("resident manager kernel could not be verified")
    elif resident_kernel is not None or resident_binding is not None:
        raise EvidenceCorrelationError("resident manager binding could not be verified")


def _validated_resident_binding(
    snapshot: Mapping[str, Any],
    run: Mapping[str, Any],
    *,
    session_id: str,
) -> dict[str, Any] | None:
    recipe_version = snapshot.get("preflight_recipe_version", 0)
    if (
        isinstance(recipe_version, bool)
        or not isinstance(recipe_version, int)
        or recipe_version < 0
    ):
        raise EvidenceCorrelationError("preflight recipe version could not be verified")
    raw_binding = snapshot.get("resident_manager_binding")
    if raw_binding is None:
        if recipe_version >= 8:
            raise EvidenceCorrelationError("resident manager binding could not be verified")
        return None
    if recipe_version < 8:
        raise EvidenceCorrelationError("resident manager binding could not be verified")
    try:
        binding = validate_resident_manager_binding(raw_binding, session_id=session_id)
    except ValueError as exc:
        raise EvidenceCorrelationError("resident manager binding could not be verified") from exc
    if binding.host != canonical_resident_manager_host(run.get("host")):
        raise EvidenceCorrelationError("resident manager host binding could not be verified")
    return binding.as_dict()


def _specialist_identity(value: Mapping[str, Any], *, activation: bool) -> tuple[str, str, str]:
    slug_key = "specialist_slug" if activation else "slug"
    version_key = "specialist_version" if activation else "version"
    hash_key = "specialist_prompt_hash" if activation else "hash"
    identity = (
        _clean(value.get(slug_key)),
        _clean(value.get(version_key)),
        _clean(value.get(hash_key)),
    )
    if not all(identity):
        raise EvidenceCorrelationError("selected specialist activation evidence is invalid")
    return identity


def _expected_activation_identities(
    selected: list[Mapping[str, Any]],
    unit_plan: object,
) -> set[tuple[str, str, str, str]]:
    selected_identities = {
        identity[0]: identity
        for identity in (_specialist_identity(row, activation=False) for row in selected)
    }
    if not isinstance(unit_plan, list) or not all(isinstance(row, Mapping) for row in unit_plan):
        raise EvidenceCorrelationError("specialist activation unit-agent plan is invalid")
    if not unit_plan:
        return {
            (f"specialist:{slug}", slug, version, content_hash)
            for slug, version, content_hash in selected_identities.values()
        }
    expected: set[tuple[str, str, str, str]] = set()
    for assignment in unit_plan:
        work_unit_id = _clean(assignment.get("work_unit_id"))
        identity = selected_identities.get(_clean(assignment.get("recommended_agent")))
        if not work_unit_id or identity is None:
            raise EvidenceCorrelationError("specialist activation unit-agent plan is invalid")
        expected.add((work_unit_id, *identity))
    return expected


def _validated_activation_identity(
    row: Mapping[str, Any],
    *,
    events: Mapping[str, Mapping[str, Any]],
    session_id: str,
    trace_id: str,
) -> tuple[str, str, str, str]:
    if (
        _clean(row.get("session_id")) != _clean(session_id)
        or _clean(row.get("trace_id")) != _clean(trace_id)
        or not _clean(row.get("id"))
        or not _clean(row.get("work_unit_id"))
        or not _clean(row.get("worker_kind"))
        or not _clean(row.get("consumed_at"))
    ):
        raise EvidenceCorrelationError("specialist activation evidence is not correlated")
    identity = _specialist_identity(row, activation=True)
    work_unit_id = _clean(row.get("work_unit_id"))
    event_id = _clean(row.get("delegation_event_id"))
    event = events.get(event_id)
    if (
        not event_id
        or event is None
        or _clean(event.get("activation_receipt_id")) != _clean(row.get("id"))
        or _clean(event.get("work_unit_id")) != work_unit_id
        or _clean(event.get("status")) not in {"started", "running", "delegated", "completed"}
    ):
        raise EvidenceCorrelationError(
            "specialist activation is not reciprocally bound to executed work"
        )
    event_worker_id = _clean(event.get("executed_worker_id"))
    event_native_run_id = _clean(event.get("native_run_id"))
    if not (event_worker_id or event_native_run_id):
        raise EvidenceCorrelationError("specialist activation has no native worker identity")
    if (
        _clean(row.get("worker_id")) != event_worker_id
        or _clean(row.get("native_run_id")) != event_native_run_id
    ):
        raise EvidenceCorrelationError("specialist activation worker identity is mismatched")
    retrieved = (
        _clean(event.get("retrieved_specialist_slug")),
        _clean(event.get("retrieved_specialist_version")),
        _clean(event.get("retrieved_specialist_prompt_hash")),
    )
    if retrieved != identity:
        raise EvidenceCorrelationError("specialist activation retrieved identity is mismatched")
    return (work_unit_id, *identity)


def _validate_specialist_activations(
    snapshot: Mapping[str, Any],
    session_id: str,
    trace_id: str,
) -> None:
    """Require every isolated selected ref to have one exact consumed grant."""

    delivery_mode = _clean(snapshot.get("delivery_mode"))
    if delivery_mode not in {"", "direct", "isolated"}:
        raise EvidenceCorrelationError("specialist delivery mode could not be verified")
    selected = snapshot.get("selected_specialists", [])
    activations = snapshot.get("specialist_activations", [])
    if not isinstance(selected, list) or not all(isinstance(row, Mapping) for row in selected):
        raise EvidenceCorrelationError("selected specialist evidence could not be verified")
    if not isinstance(activations, list) or not all(
        isinstance(row, Mapping) for row in activations
    ):
        raise EvidenceCorrelationError("specialist activation evidence could not be verified")
    if delivery_mode != "isolated":
        return

    request_kind = _clean(snapshot.get("request_kind"))
    selection_required = snapshot.get(
        "selection_required",
        request_kind == "nontrivial",
    )
    if not isinstance(selection_required, bool):
        raise EvidenceCorrelationError("turn specialist-selection policy could not be verified")
    delegation_rows = snapshot.get("delegations", [])
    expected = _expected_activation_identities(
        selected,
        snapshot.get("unit_agent_plan", []),
    )
    events = {
        _clean(event.get("id")): event
        for event in delegation_rows
        if isinstance(event, Mapping) and _clean(event.get("id"))
    }
    actual: set[tuple[str, str, str, str]] = set()
    for row in activations:
        activation_identity = _validated_activation_identity(
            row,
            events=events,
            session_id=session_id,
            trace_id=trace_id,
        )
        if activation_identity in actual:
            raise EvidenceCorrelationError("specialist activation evidence is not one-use")
        actual.add(activation_identity)
    claimed = {_clean(slug) for slug in snapshot.get("specialists", []) if _clean(slug)}
    activated = {identity[1] for identity in actual}
    if claimed != activated:
        raise EvidenceCorrelationError(
            "specialist activation loaded-specialist evidence is mismatched"
        )
    if not actual.issubset(expected):
        raise EvidenceCorrelationError(
            "specialist activation was not assigned by this turn's unit-agent plan"
        )
    unit_plan = snapshot.get("unit_agent_plan", [])
    required = expected
    if unit_plan:
        selected_identities = {
            identity[0]: identity
            for identity in (_specialist_identity(row, activation=False) for row in selected)
        }
        executed_work_units = {
            _clean(event.get("work_unit_id"))
            for event in delegation_rows
            if isinstance(event, Mapping)
            and _clean(event.get("status")) in {"started", "running", "delegated", "completed"}
        }
        required = {
            (
                _clean(assignment.get("work_unit_id")),
                *selected_identities[_clean(assignment.get("recommended_agent"))],
            )
            for assignment in unit_plan
            if _clean(assignment.get("work_unit_id")) in executed_work_units
            and _clean(assignment.get("recommended_agent")) in selected_identities
        }
    if selection_required and required != actual:
        raise EvidenceCorrelationError("selected specialist activation is incomplete")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    # Header values are intentionally one line.  Preserve words, remove line
    # breaks that would violate the six-line contract.
    return " ".join(text.splitlines()).strip()


def _is_present(value: Any) -> bool:
    text = _clean(value)
    return bool(text) and text.lower() not in _EMPTY_VALUES


def _starts_with_header(response_text: str) -> bool:
    lines = response_text.splitlines()
    return len(lines) >= len(HEADER_FIELDS) and all(
        lines[index].startswith(f"{label}:") for index, (_key, label) in enumerate(HEADER_FIELDS)
    )


def _split_header_body(response_text: str) -> tuple[list[str], str]:
    lines = response_text.splitlines()
    header_lines = lines[: len(HEADER_FIELDS)]
    body = (
        "\n".join(lines[len(HEADER_FIELDS) :]).lstrip("\n")
        if len(lines) > len(HEADER_FIELDS)
        else ""
    )
    return header_lines, body


def parse_header(response_text: str) -> dict[str, str]:
    """Parse the six-line Agency header from the beginning of response_text.

    Missing or malformed lines are omitted from the returned mapping.
    """
    parsed: dict[str, str] = {}
    for line in response_text.splitlines()[: len(HEADER_FIELDS)]:
        if ":" not in line:
            continue
        label, value = line.split(":", 1)
        key = _LABEL_TO_KEY.get(label.strip().lower())
        if key:
            parsed[key] = value.strip()
    return parsed


def format_header(fields: Mapping[str, Any]) -> str:
    """Format fields as the exact six-line Agency header."""
    return "\n".join(f"{label}: {_clean(fields.get(key, ''))}" for key, label in HEADER_FIELDS)


def validate_header(response_text: str) -> tuple[bool, list[str]]:
    """Validate that response_text starts with all six non-empty header fields."""
    lines = response_text.splitlines()
    missing: list[str] = []
    if len(lines) < len(HEADER_FIELDS):
        # Continue checking available lines so callers get specific diagnostics.
        pass

    parsed = parse_header(response_text)
    for index, (key, label) in enumerate(HEADER_FIELDS):
        if index >= len(lines):
            missing.append(key)
            continue
        line = lines[index]
        expected_prefix = f"{label}:"
        if not line.startswith(expected_prefix):
            missing.append(key)
            continue
        if not _is_present(parsed.get(key, "")):
            missing.append(key)
    return (not missing, missing)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def correlation_error(
    store: Any,
    session_id: str,
    trace_id: str,
    *,
    require_active: bool = False,
) -> str:
    """Return a deterministic correlation failure, or an empty string.

    Historical evidence readers intentionally accept terminal turns. Completion
    gates pass require_active=True so a finalized trace cannot be replayed.
    """
    if not session_id:
        return "session_id is required for authoritative Agency evidence"
    if not trace_id:
        return "trace_id is required for authoritative Agency evidence"
    if store is None:
        return ""
    getter = getattr(store, "get_run", None)
    if not callable(getter):
        return "evidence store cannot verify turn correlation"
    try:
        run = getter(trace_id)
    except Exception:
        return "turn correlation could not be verified"
    if not isinstance(run, Mapping):
        return "trace_id does not identify a recorded Agency turn"
    try:
        recorded_session = _clean(run.get("session_id"))
        status = _clean(run.get("status"))
    except Exception:
        return "turn correlation could not be verified"
    if recorded_session != _clean(session_id):
        return "trace_id does not belong to session_id"
    if require_active and status not in {"active", "evidence_only"}:
        if not status:
            return "turn lifecycle status could not be verified"
        return "trace_id identifies a terminal Agency turn"
    return ""


def _validate_completion_snapshot(
    snapshot: Any,
    session_id: str,
    trace_id: str,
    *,
    require_active: bool = True,
    validate_activations: bool = True,
) -> dict[str, Any]:
    """Validate one already-read snapshot without consulting the Store again."""

    if not isinstance(snapshot, Mapping):
        raise EvidenceCorrelationError("completion evidence snapshot could not be verified")
    run = snapshot.get("run")
    if not isinstance(run, Mapping):
        raise EvidenceCorrelationError("completion evidence run could not be verified")

    snapshot_session = _clean(snapshot.get("session_id"))
    snapshot_trace = _clean(snapshot.get("trace_id"))
    run_session = _clean(run.get("session_id"))
    run_trace = _clean(run.get("trace_id"))
    if snapshot_session != _clean(session_id) or run_session != _clean(session_id):
        raise EvidenceCorrelationError("trace_id does not belong to session_id")
    if snapshot_trace != _clean(trace_id) or run_trace != _clean(trace_id):
        raise EvidenceCorrelationError("trace_id does not identify the requested Agency turn")

    status = _clean(snapshot.get("status"))
    run_status = _clean(run.get("status"))
    if not status or status != run_status:
        raise EvidenceCorrelationError("turn lifecycle status could not be verified")
    if require_active and status not in {"active", "evidence_only"}:
        raise EvidenceCorrelationError("trace_id identifies a terminal Agency turn")
    if require_active and (
        _clean(run.get("ended_at")) or _clean(run.get("terminal_finalization_id"))
    ):
        raise EvidenceCorrelationError("active turn lifecycle binding could not be verified")

    request_kind = _clean(snapshot.get("request_kind"))
    run_request_kind = _clean(run.get("request_kind"))
    if request_kind != run_request_kind or request_kind not in {"trivial", "nontrivial"}:
        raise EvidenceCorrelationError("turn request kind could not be verified")

    selection_required = snapshot.get(
        "selection_required",
        request_kind == "nontrivial",
    )
    run_selection_required = run.get(
        "selection_required",
        run_request_kind == "nontrivial",
    )
    if (
        not isinstance(selection_required, bool)
        or not isinstance(run_selection_required, bool)
        or selection_required != run_selection_required
        or (request_kind == "nontrivial") != selection_required
    ):
        raise EvidenceCorrelationError("turn specialist-selection policy could not be verified")

    turn_kind = _clean(
        snapshot.get(
            "turn_kind",
            "new_intent" if selection_required else "acknowledgement",
        )
    )
    run_turn_kind = _clean(
        run.get(
            "turn_kind",
            "new_intent" if run_selection_required else "acknowledgement",
        )
    )
    if turn_kind != run_turn_kind or turn_kind not in {
        "acknowledgement",
        "conversation",
        "control",
        "continuation",
        "new_intent",
        "revision",
    }:
        raise EvidenceCorrelationError("turn intent classification could not be verified")

    revision = snapshot.get("evidence_revision")
    run_revision = run.get("evidence_revision")
    if (
        isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision <= 0
        or revision != run_revision
    ):
        raise EvidenceCorrelationError("completion evidence revision could not be verified")

    _validate_snapshot_collections(snapshot)
    resident_binding = _validated_resident_binding(
        snapshot,
        run,
        session_id=snapshot_session,
    )
    if validate_activations:
        _validate_specialist_activations(snapshot, session_id, trace_id)
    normalized = dict(snapshot)
    normalized["resident_managers"] = list(snapshot.get("resident_managers", []))
    normalized["resident_manager_binding"] = resident_binding
    normalized["selection_required"] = selection_required
    normalized["turn_kind"] = turn_kind
    normalized_run = dict(run)
    normalized_run["selection_required"] = run_selection_required
    normalized_run["turn_kind"] = run_turn_kind
    normalized["run"] = normalized_run
    return normalized


def _is_legacy_unclassified_evidence_snapshot(
    snapshot: object,
    session_id: str,
    trace_id: str,
) -> bool:
    """Recognize old tool-only evidence rows that predate turn classification."""

    if not isinstance(snapshot, Mapping):
        return False
    run = snapshot.get("run")
    return bool(
        isinstance(run, Mapping)
        and _clean(snapshot.get("session_id")) == _clean(session_id)
        and _clean(run.get("session_id")) == _clean(session_id)
        and _clean(snapshot.get("trace_id")) == _clean(trace_id)
        and _clean(run.get("trace_id")) == _clean(trace_id)
        and _clean(snapshot.get("status")) == "evidence_only"
        and _clean(run.get("status")) == "evidence_only"
        and not _clean(snapshot.get("request_kind"))
        and not _clean(run.get("request_kind"))
    )


def read_completion_evidence_snapshot(
    store: Any,
    session_id: str,
    trace_id: str,
    *,
    validate_activations: bool = True,
) -> dict[str, Any]:
    """Read and validate one atomic completion-evidence snapshot."""

    if not session_id:
        raise EvidenceCorrelationError("session_id is required for authoritative Agency evidence")
    if not trace_id:
        raise EvidenceCorrelationError("trace_id is required for authoritative Agency evidence")
    getter = getattr(store, "get_completion_evidence_snapshot", None)
    if not callable(getter):
        raise EvidenceCorrelationError("completion evidence snapshot could not be verified")
    try:
        snapshot = getter(session_id, trace_id)
    except ValueError as exc:
        message = _clean(exc)
        if message not in {
            "trace_id does not identify a recorded Agency turn",
            "trace_id does not belong to session_id",
        }:
            message = "completion evidence snapshot could not be verified"
        raise EvidenceCorrelationError(message) from exc
    except Exception as exc:
        raise EvidenceCorrelationError(
            "completion evidence snapshot could not be verified"
        ) from exc
    return _validate_completion_snapshot(
        snapshot,
        session_id,
        trace_id,
        validate_activations=validate_activations,
    )


def _read_evidence(
    store: Any,
    method_name: str,
    *args: str,
    strict: bool,
) -> Any:
    """Read one evidence projection, optionally failing closed on store errors."""
    try:
        getter = getattr(store, method_name, None)
        if not callable(getter):
            raise AttributeError(f"evidence store does not provide {method_name}")
        return getter(*args)
    except Exception as exc:
        if strict:
            label = method_name.removeprefix("get_").replace("_", " ")
            raise EvidenceCorrelationError(f"{label} evidence could not be verified") from exc
        return None


def _get_loaded_specialists(
    store: Any,
    session_id: str,
    trace_id: str,
    *,
    strict: bool = False,
) -> list[str]:
    if not store or not session_id or not trace_id:
        return []
    rows = _read_evidence(
        store,
        "get_specialists_for_trace",
        session_id,
        trace_id,
        strict=strict,
    )
    return _dedupe(list(rows or []))


def _get_delegations(
    store: Any,
    session_id: str,
    trace_id: str,
    *,
    strict: bool = False,
) -> list[dict[str, Any]]:
    if not store or not session_id or not trace_id:
        return []
    rows = _read_evidence(store, "get_delegations", trace_id, strict=strict)
    return [dict(row) for row in rows or [] if _clean(row.get("session_id")) == _clean(session_id)]


def _get_skills(
    store: Any,
    session_id: str,
    trace_id: str,
    *,
    strict: bool = False,
) -> list[str]:
    if not store or not session_id or not trace_id:
        return []
    rows = _read_evidence(
        store,
        "get_skills_for_trace",
        session_id,
        trace_id,
        strict=strict,
    )
    return _dedupe(list(rows or []))


def _latest_model_receipt(
    store: Any,
    session_id: str,
    trace_id: str,
    *,
    strict: bool = False,
) -> dict[str, Any] | None:
    if not store or not session_id or not trace_id:
        return None
    row = _read_evidence(store, "get_model_receipt", trace_id, strict=strict)
    if not row or _clean(row.get("session_id")) != _clean(session_id):
        return None
    return dict(row)


_MODEL_GROUP_COMPLEXITY: dict[str, str] = {
    "task-chunk-planner": "planner",
    "task-general": "general",
    "task-implementation": "implementation",
    "task-agency-router": "router",
}


def _complexity_for_model_group(model_group: str) -> str:
    """Return a human-readable complexity tier for a LiteLLM model group."""
    return _MODEL_GROUP_COMPLEXITY.get(_clean(model_group), "")


def _model_line(receipt: Mapping[str, Any] | None, requested_model: str) -> str:
    requested = (
        _clean((receipt or {}).get("requested_model")) or _clean(requested_model) or "unknown"
    )
    tier = _complexity_for_model_group(requested)
    tier_prefix = f"[{tier}] " if tier else ""
    if not receipt:
        return f"{tier_prefix}{requested} -> unavailable - no model receipt recorded"

    resolved_model = _clean(receipt.get("resolved_model"))
    resolved_provider = _clean(receipt.get("resolved_provider"))
    source = _clean(receipt.get("source")) or "unknown"
    status = _clean(receipt.get("status"))
    model_group = _clean(receipt.get("model_group"))

    if not resolved_model or resolved_model == "unavailable":
        reason = (
            status
            if status and status not in {"success", "unknown"}
            else "unavailable - no resolved model telemetry"
        )
        if source.casefold() == "litellm" and model_group:
            reason = f"{reason} via LiteLLM router {model_group}"
        return f"{tier_prefix}{requested} -> {reason}"

    target = f"{resolved_provider}/{resolved_model}" if resolved_provider else resolved_model
    if source.casefold() == "litellm" and model_group:
        target = f"{target} via LiteLLM router {model_group}"
    elif model_group and model_group != resolved_model:
        target = f"{target} via {model_group}"
    if source.casefold() != "litellm" or not model_group:
        target = f"{target} ({source})"
    return f"{tier_prefix}{requested} -> {target}"


def _delegation_line(delegations: list[dict[str, Any]]) -> str:
    if not delegations:
        return "none"
    completed: list[str] = []
    reasons: list[str] = []
    for event in delegations:
        specialist = _clean(event.get("retrieved_specialist_slug"))
        worker_kind = _clean(event.get("executed_worker_kind"))
        backend = _clean(event.get("backend"))
        status = _clean(event.get("status"))
        skip_reason = _clean(event.get("skip_reason")) or _clean(event.get("error"))
        if specialist and status in {"completed", "running", "started", "delegated"}:
            execution = "/".join(_dedupe([worker_kind, backend]))
            completed.append(f"{specialist} via {execution}" if execution else specialist)
        elif status in {"completed", "running", "started", "delegated"}:
            reasons.append("executed worker has no validated Agency specialist")
        elif skip_reason:
            reasons.append(skip_reason)
    if completed:
        return ", ".join(_dedupe(completed))
    if reasons:
        return f"none - {_dedupe(reasons)[0]}"
    return "none - delegation suggested but not executed"


def _bounded_evidence_codes(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    for item in value:
        code = str(item or "").strip().casefold()[:96]
        if _EVIDENCE_CODE.fullmatch(code) is not None and code not in result:
            result.append(code)
            if len(result) >= _MAX_HEADER_CODES:
                break
    return result


def _ready_routing_receipt(
    store: Any,
    session_id: str,
    trace_id: str,
    snapshot: Mapping[str, Any],
) -> dict[str, Any] | None:
    from agency_runtime.core.selector.receipt_projection import (
        normalize_durable_routing_receipt,
    )

    getter = getattr(store, "get_ready_routing_receipt", None)
    revision = snapshot.get("evidence_revision")
    if (
        not callable(getter)
        or isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision <= 0
    ):
        return None
    try:
        value = getter(
            session_id,
            trace_id,
            evidence_revision=revision,
        )
    except Exception as exc:
        raise EvidenceCorrelationError("routing receipt evidence could not be verified") from exc
    return normalize_durable_routing_receipt(value)


def _header_reason_codes(
    snapshot: Mapping[str, Any] | None,
    receipt: Mapping[str, Any] | None,
) -> list[str]:
    values: list[str] = []
    if snapshot is not None:
        values.extend(_bounded_evidence_codes(snapshot.get("reason_codes")))
    if receipt is not None:
        values.extend(_bounded_evidence_codes(receipt.get("reason_codes")))
    return _bounded_evidence_codes(values)


def _header_effect_codes(
    snapshot: Mapping[str, Any] | None,
    receipt: Mapping[str, Any] | None,
) -> list[str]:
    values = _bounded_evidence_codes(receipt.get("effect_codes")) if receipt is not None else []
    if snapshot is not None:
        if snapshot.get("specialists"):
            values.append("specialist_context_loaded")
        if snapshot.get("skills"):
            values.append("skill_context_loaded")
        model_receipt = snapshot.get("model_receipt")
        if isinstance(model_receipt, Mapping):
            values.append("model_receipt_recorded")
        delegations = snapshot.get("delegations")
        if isinstance(delegations, list) and any(
            isinstance(row, Mapping)
            and _clean(row.get("retrieved_specialist_slug"))
            and _clean(row.get("status")) in {"completed", "running", "started", "delegated"}
            for row in delegations
        ):
            values.append("delegated_specialist_executed")
    return _bounded_evidence_codes(values)


def _noneish_agency_line(value: str) -> bool:
    text = _clean(value).lower().rstrip(".!")
    return text == "none" or text.startswith(("none ", "none-", "none--"))


def _non_actionable_delegation_none(value: str) -> bool:
    """Return True when a none-delegation claim lacks a concrete blocker."""

    text = _clean(value).lower().rstrip(".!")
    return text in {
        "none",
        "none - no delegation executed",
        "none - delegation suggested but not executed",
    }


def _planned_delegation_strengths(snapshot: Mapping[str, Any]) -> dict[str, str] | None:
    """Return current-plan strengths, or None for a legacy evidence snapshot."""

    recipe_version = snapshot.get("preflight_recipe_version", 0)
    if not isinstance(recipe_version, int) or isinstance(recipe_version, bool):
        return None
    if recipe_version < 11:
        return None
    raw_plan = snapshot.get("unit_agent_plan", [])
    if not isinstance(raw_plan, list):
        raise EvidenceCorrelationError("delegation strength plan could not be verified")
    strengths: dict[str, str] = {}
    for item in raw_plan:
        if not isinstance(item, Mapping):
            raise EvidenceCorrelationError("delegation strength plan could not be verified")
        work_unit_id = _clean(item.get("work_unit_id"))
        strength = _clean(item.get("delegation_strength"))
        if (
            not work_unit_id
            or strength not in {"optional", "preferred", "strongly_preferred"}
            or work_unit_id in strengths
        ):
            raise EvidenceCorrelationError("delegation strength plan could not be verified")
        strengths[work_unit_id] = strength
    return strengths


def _strong_delegation_correction(
    snapshot: Mapping[str, Any],
    open_delegations: list[dict[str, Any]],
) -> CompletionPolicyViolation | None:
    strengths = _planned_delegation_strengths(snapshot)
    if strengths is None:
        return None
    strong = [
        row
        for row in open_delegations
        if strengths.get(_clean(row.get("work_unit_id"))) == "strongly_preferred"
    ]
    if not strong:
        return None
    run = snapshot.get("run")
    host = _clean(run.get("host")) if isinstance(run, Mapping) else ""
    rows = "; ".join(
        f"work_unit_id={_clean(row.get('work_unit_id'))}, "
        f"recommended_agent={_clean(row.get('recommended_agent'))}"
        for row in strong[:16]
    )
    return {
        "message": (
            "AGENCY DELEGATION CORRECTION (one pass only): strongly_preferred native "
            f"work remains unresolved: {rows}. {native_delegation_instruction(host)} "
            "Delegation is expected to keep the parent responsive and preserve isolated "
            "specialist execution. Record either authoritative native worker/run evidence "
            "or one explicit decline receipt for every listed work unit."
        ),
        "missing": ["delegation_execution"],
    }


def _completion_snapshot_violation(error: EvidenceCorrelationError) -> CompletionPolicyViolation:
    detail = _clean(error)
    if "specialist activation" in detail:
        return {
            "message": (
                "AGENCY SPECIALIST ACTIVATION INCOMPLETE: Every assigned isolated "
                "work unit must consume its own exact-version, one-use specialist "
                "activation receipt before finalization."
            ),
            "missing": ["specialist_activation"],
        }
    if "terminal Agency turn" in detail:
        return {
            "message": (
                "AGENCY TURN TERMINAL: This trace has already reached a terminal "
                "completion state and cannot be finalized or reused. Do not retry "
                "this response with the same trace_id; begin a new user turn."
            ),
            "missing": ["correlation"],
        }
    correlation_markers = (
        "session_id is required",
        "trace_id is required",
        "trace_id does not identify",
        "trace_id does not belong",
    )
    if any(marker in detail for marker in correlation_markers):
        return {
            "message": (
                f"AGENCY CORRELATION INVALID: {detail}. Re-run Agency preflight for "
                "this turn and retry finalization with the returned session_id and "
                "trace_id."
            ),
            "missing": ["correlation"],
        }
    return {
        "message": (
            "AGENCY EVIDENCE VERIFICATION UNAVAILABLE: Turn-scoped specialist, "
            "delegation, model, skill, or request-kind evidence could not be "
            "verified from one atomic snapshot. Do not publish this response; "
            "restore the evidence store and retry."
        ),
        "missing": ["evidence_verification"],
    }


def validate_completion_policy(
    response_text: str,
    *,
    session_id: str,
    trace_id: str,
    store: Any,
    model: str = "",
    evidence_snapshot: Mapping[str, Any] | None = None,
) -> CompletionPolicyViolation | None:
    """Validate every terminal-accept policy against one authoritative turn.

    This is the shared completion boundary for native verification and public
    finalization. It deliberately returns a structured revision instead of
    raising so host adapters can translate the same decision into their native
    block or retry shape.
    """

    try:
        snapshot = (
            _validate_completion_snapshot(evidence_snapshot, session_id, trace_id)
            if evidence_snapshot is not None
            else read_completion_evidence_snapshot(store, session_id, trace_id)
        )
    except EvidenceCorrelationError as error:
        return _completion_snapshot_violation(error)

    valid, missing = validate_header(response_text)
    if not valid:
        return {
            "message": (
                "Your response is missing or has malformed Agency header fields: "
                + ", ".join(missing)
                + ". Rewrite the response starting with the exact six-line Agency header."
            ),
            "missing": missing,
        }

    parsed = parse_header(response_text)
    loaded = parsed.get("agencies_loaded", "")
    delegated = parsed.get("agencies_delegated", "")
    try:
        specialists = _dedupe(list(snapshot["specialists"]))
        resident_managers = _dedupe(list(snapshot.get("resident_managers", [])))
        loaded_agents = _dedupe([*resident_managers, *specialists])
        delegations = [dict(row) for row in snapshot["delegations"]]
        open_delegations = [row for row in delegations if _clean(row.get("status")) == "suggested"]
        selection_required = bool(snapshot["selection_required"])
    except (KeyError, TypeError, ValueError):
        return {
            "message": (
                "AGENCY EVIDENCE VERIFICATION UNAVAILABLE: Turn-scoped specialist, "
                "delegation, or request-kind evidence could not be verified. "
                "Do not publish this response; restore the evidence store and retry."
            ),
            "missing": ["evidence_verification"],
        }

    requires_agency_evidence = bool(
        session_id and (loaded_agents or selection_required or specialists)
    ) or bool(open_delegations)
    if requires_agency_evidence and _noneish_agency_line(loaded):
        actual = ", ".join(loaded_agents) if loaded_agents else "the actual loaded specialist"
        run = snapshot.get("run")
        host = run.get("host") if isinstance(run, Mapping) else ""
        loading = specialist_load_guidance(host, session_id, trace_id)
        next_action = (
            "Use the current turn's resident-manager evidence."
            if resident_managers
            else f"If no specialist context is loaded, {loading} first."
        )
        return {
            "message": (
                "AGENCY HEADER INVALID: This turn has Agency context but "
                "Agency/Agencies loaded starts with 'none'. "
                f"Rewrite the header with {actual}. {next_action}"
            ),
            "missing": ["agencies_loaded"],
        }

    try:
        strengths = _planned_delegation_strengths(snapshot)
        strong_correction = _strong_delegation_correction(snapshot, open_delegations)
    except EvidenceCorrelationError:
        return {
            "message": (
                "AGENCY EVIDENCE VERIFICATION UNAVAILABLE: Delegation strength evidence "
                "could not be verified. Do not publish this response; restore the evidence "
                "store and retry."
            ),
            "missing": ["evidence_verification"],
        }
    if strong_correction is not None:
        return strong_correction
    if strengths is None and open_delegations and _non_actionable_delegation_none(delegated):
        return {
            "message": (
                "DELEGATION OPPORTUNITY WAS DETECTED but agencies_delegated has no "
                "executed delegation or concrete blocker. Dispatch at least one independent "
                f"work unit. {NATIVE_DELEGATION_GUIDANCE} Then report the executed "
                "delegation in the Agency header. If delegation is "
                "impossible, state the concrete blocker instead of writing bare 'none'."
            ),
            "missing": ["agencies_delegated"],
        }

    header_snapshot: Mapping[str, Any] = snapshot
    if strengths is not None and open_delegations:
        # Optional and preferred suggestions are planning evidence, not execution.
        # Keep them in the durable activity stream while excluding them from the
        # executed-delegation header projection. Strong rows returned above.
        open_ids = {_clean(row.get("id")) for row in open_delegations}
        header_snapshot = {
            **snapshot,
            "delegations": [row for row in delegations if _clean(row.get("id")) not in open_ids],
        }

    try:
        authoritative = fill_header_fields(
            parsed,
            session_id,
            store,
            model,
            trace_id,
            evidence_snapshot=header_snapshot,
        )
    except EvidenceCorrelationError:
        return {
            "message": (
                "AGENCY EVIDENCE VERIFICATION UNAVAILABLE: Authoritative turn evidence "
                "could not be read. Do not publish this response; restore the evidence "
                "store and retry."
            ),
            "missing": ["evidence_verification"],
        }
    evidence_fields = HEADER_FIELDS
    mismatches = [
        (key, label, authoritative[key])
        for key, label in evidence_fields
        if _clean(parsed.get(key)) != _clean(authoritative[key])
    ]
    if mismatches:
        corrections = "; ".join(f"{label}: {value}" for _key, label, value in mismatches)
        return {
            "message": (
                "AGENCY HEADER DOES NOT MATCH RECORDED EVIDENCE. "
                "Do not claim unrecorded specialist, delegation, or model activity. "
                f"Rewrite these fields exactly: {corrections}"
            ),
            "missing": [key for key, _label, _value in mismatches],
        }
    return None


def evaluate_completion_policy(
    response_text: str,
    *,
    session_id: str,
    trace_id: str,
    store: Any,
    model: str = "",
) -> CompletionPolicyDecision:
    """Return an internal decision and the exact evidence revision it consumed."""

    try:
        # Read a structurally authoritative snapshot first so a correctable
        # missing activation can retain its evidence revision and consume the
        # bounded Stop retry.  validate_completion_policy below still performs
        # the full activation check before any accept decision.
        snapshot = read_completion_evidence_snapshot(
            store,
            session_id,
            trace_id,
            validate_activations=False,
        )
    except EvidenceCorrelationError as error:
        violation = _completion_snapshot_violation(error)
        return {
            "action": "continue",
            "message": violation["message"],
            "missing": violation["missing"],
        }
    violation = validate_completion_policy(
        response_text,
        session_id=session_id,
        trace_id=trace_id,
        store=store,
        model=model,
        evidence_snapshot=snapshot,
    )
    decision: CompletionPolicyDecision = {
        "action": "continue" if violation is not None else "accept",
        "missing": violation["missing"] if violation is not None else [],
        "evidence_revision": int(snapshot["evidence_revision"]),
    }
    if violation is not None:
        decision["message"] = violation["message"]
        if "delegation_execution" in violation["missing"]:
            decision["delegation_strength"] = "strongly_preferred"
    return decision


def fill_header_fields(
    fields: Mapping[str, Any] | None,
    session_id: str,
    store: Any,
    model: str = "",
    trace_id: str = "",
    *,
    evidence_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Reconcile header fields with authoritative evidence for one turn.

    All six fields are evidence fields: authored values never outrank current-
    turn runtime records. Explanatory lines expose bounded reason/effect codes
    and report unavailable when the authoritative evidence is absent.
    """
    filled = {key: _clean((fields or {}).get(key, "")) for key in _REQUIRED_KEYS}

    snapshot: dict[str, Any] | None = None
    if evidence_snapshot is not None:
        snapshot = _validate_completion_snapshot(
            evidence_snapshot,
            session_id,
            trace_id,
        )
    elif (
        store is not None
        and session_id
        and trace_id
        and callable(getattr(store, "get_completion_evidence_snapshot", None))
    ):
        raw_snapshot = store.get_completion_evidence_snapshot(session_id, trace_id)
        try:
            snapshot = _validate_completion_snapshot(raw_snapshot, session_id, trace_id)
        except EvidenceCorrelationError:
            if not _is_legacy_unclassified_evidence_snapshot(
                raw_snapshot,
                session_id,
                trace_id,
            ):
                raise

    if snapshot is None:
        error = correlation_error(store, session_id, trace_id)
        if store is not None and error:
            raise EvidenceCorrelationError(error)
        agents = _get_loaded_specialists(
            store,
            session_id,
            trace_id,
            strict=store is not None,
        )
        delegations = _get_delegations(
            store,
            session_id,
            trace_id,
            strict=store is not None,
        )
        skills = _get_skills(
            store,
            session_id,
            trace_id,
            strict=store is not None,
        )
        model_receipt = _latest_model_receipt(
            store,
            session_id,
            trace_id,
            strict=store is not None,
        )
        routing_receipt = None
    else:
        agents = _dedupe(
            [
                *list(snapshot.get("resident_managers", [])),
                *list(snapshot["specialists"]),
            ]
        )
        delegations = [dict(row) for row in snapshot["delegations"]]
        skills = _dedupe(list(snapshot["skills"]))
        raw_model_receipt = snapshot.get("model_receipt")
        model_receipt = dict(raw_model_receipt) if isinstance(raw_model_receipt, Mapping) else None
        routing_receipt = _ready_routing_receipt(
            store,
            session_id,
            trace_id,
            snapshot,
        )

    filled["agencies_loaded"] = ", ".join(agents) if agents else "none"
    filled["agencies_delegated"] = _delegation_line(delegations)
    filled["skills_loaded"] = ", ".join(skills) if skills else "none"
    filled["actual_model_selected"] = _model_line(model_receipt, model)
    filled["why"] = humanize_reason_codes(_header_reason_codes(snapshot, routing_receipt))
    filled["how_it_shaped_outcome"] = humanize_effect_codes(
        _header_effect_codes(snapshot, routing_receipt)
    )

    return filled


def finalize_header(
    response_text: str,
    session_id: str,
    store: Any,
    model: str,
    trace_id: str = "",
) -> str:
    """Ensure response_text starts with a complete Agency header.

    Every field is overwritten from current-turn SQLite evidence. Explanatory
    lines humanize bounded reason/effect codes without changing the durable
    machine-readable receipt.
    """
    valid, _ = validate_header(response_text)
    has_header = _starts_with_header(response_text)
    existing = parse_header(response_text) if has_header else {}
    _, body = _split_header_body(response_text) if has_header else ([], response_text.lstrip("\n"))
    if not has_header and not valid:
        body = response_text.lstrip("\n")
    fields = fill_header_fields(existing, session_id, store, model, trace_id)
    header = format_header(fields)
    return f"{header}\n\n{body}" if body else header


__all__ = [
    "HEADER_FIELDS",
    "CompletionPolicyDecision",
    "CompletionPolicyViolation",
    "EvidenceCorrelationError",
    "correlation_error",
    "evaluate_completion_policy",
    "fill_header_fields",
    "finalize_header",
    "format_header",
    "parse_header",
    "read_completion_evidence_snapshot",
    "validate_completion_policy",
    "validate_header",
]
