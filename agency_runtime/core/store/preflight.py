"""Atomic preflight reservation, fencing, replay, and cleanup persistence."""

from __future__ import annotations

import copy
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.codex_native_plan_scope import (
    CodexNativePlanScope,
    deserialize_codex_native_plan_scope,
    serialize_codex_native_plan_scope,
    validate_codex_native_plan_scope,
)
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.installer_contracts import (
    HOOK_TIMEOUT_BUFFER_SECONDS,
    MAX_HOOK_TIMEOUT_SECONDS,
)
from agency_runtime.core.native_child_activation import build_native_child_evidence_contract
from agency_runtime.core.preflight_failure import (
    MAX_PREFLIGHT_FAILURE_PROVIDER_ATTEMPTS_BYTES,
    MAX_PREFLIGHT_FAILURE_REASON_CODES_BYTES,
    PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
    default_preflight_failure_receipt,
    project_preflight_failure_receipt,
)
from agency_runtime.core.preflight_versions import (
    PREFLIGHT_REPLAY_RECIPE_VERSION,
    SUPPORTED_PREFLIGHT_RECIPE_VERSIONS,
)
from agency_runtime.core.receipts.ingress import (
    ReceiptProvenance as _ReceiptProvenance,
)
from agency_runtime.core.receipts.ingress import (
    normalize_receipt_ingress as _normalize_receipt_ingress,
)
from agency_runtime.core.resident_manager_binding import (
    canonical_resident_manager_host,
    validate_resident_manager_binding,
)
from agency_runtime.core.resident_managers import (
    is_current_resident_manager_kernel_reference,
    is_resident_manager_slug,
)
from agency_runtime.core.specialist_contracts import MAX_DURABLE_SPECIALIST_REFERENCES
from agency_runtime.core.store.projections import (
    RUN_CONTENT_LIMIT as _RUN_CONTENT_LIMIT,
)
from agency_runtime.core.store.projections import (
    project_run_metadata,
    redact_sensitive_text,
)
from agency_runtime.core.store.queries import project_routing_decision
from agency_runtime.core.store.resident_binding import ResidentManagerBindingStoreMixin
from agency_runtime.core.store.schema import STORE_CLOCK_SQL
from agency_runtime.core.store.version_identity import (
    MAX_VERSION_IDENTITY_BYTES,
    is_valid_version_identity,
)
from agency_runtime.core.turn_intent import TURN_CLASSIFIER_VERSION
from agency_runtime.core.unit_assignment import (
    native_child_evidence_requirements,
    project_unit_assignment_agents,
)

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_WORK_UNIT_ID_PATTERN = re.compile(r"^unit-[0-9a-f]{10}$")
_MAX_RECIPE_BYTES = 48_000
_MAX_RECIPE_NODES = 2_048
_CONTINUATION_GUARD_VERSION = 1
_MAX_SELECTION_REFS = 16
_TURN_KINDS = frozenset(
    {
        "acknowledgement",
        "conversation",
        "control",
        "continuation",
        "new_intent",
        "revision",
    }
)


@dataclass(frozen=True, slots=True)
class _PreflightRequest:
    session_id: str
    trace_id: str
    reservation_token: str
    fingerprint: str
    request_kind: str
    host: str
    user_message: str
    metadata: str | None


@dataclass(frozen=True, slots=True)
class _ReadyEvidence:
    session_id: str
    trace_id: str
    attempt_token: str
    host: str
    recipe: dict[str, Any]
    encoded_recipe: str
    delivery_mode: str
    specialist_refs: list[dict[str, Any]]
    suggestions: list[dict[str, Any]]
    routing: dict[str, Any]
    model_receipts: list[dict[str, Any]]
    pending_hiring_commits: list[Any]
    resident_manager_binding: dict[str, Any] | None


@dataclass(slots=True)
class _ReadyTransactionState:
    rollback_requested: bool = False


class _ReadyTransactionConnection:
    """Keep governed Store helpers inside the preflight ready transaction."""

    def __init__(self, connection: Any, state: _ReadyTransactionState):
        self._connection = connection
        self._state = state

    def execute(self, sql: str, parameters: object = ()) -> Any:
        if self._state.rollback_requested:
            raise RuntimeError("preflight ready transaction requested rollback")
        if str(sql).lstrip().upper().startswith("BEGIN"):
            return self._connection.execute("SELECT 1")
        return self._connection.execute(sql, parameters)

    def executemany(self, sql: str, parameters: object) -> Any:
        if self._state.rollback_requested:
            raise RuntimeError("preflight ready transaction requested rollback")
        return self._connection.executemany(sql, parameters)

    def commit(self) -> None:
        if self._state.rollback_requested:
            raise RuntimeError("preflight ready transaction requested rollback")

    def rollback(self) -> None:
        self._state.rollback_requested = True

    def close(self) -> None:
        return None

    def __enter__(self) -> _ReadyTransactionConnection:
        return self

    def __exit__(self, exc_type: object, _exc: object, _tb: object) -> bool:
        if exc_type is not None:
            self._state.rollback_requested = True
        return False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)


def _ready_transaction_store(store: Any, connection: Any) -> tuple[Any, _ReadyTransactionState]:
    state = _ReadyTransactionState()
    bound = copy.copy(store)
    proxy = _ReadyTransactionConnection(connection, state)
    bound._connect = lambda: proxy
    return bound, state


def _request_fingerprint(value: object) -> str:
    """Extract a fixed-width request identity from projected run metadata."""
    if not value:
        return ""
    try:
        parsed = safe_load_bounded_json(
            str(value),
            maximum_bytes=4_096,
            maximum_depth=4,
            maximum_nodes=32,
        )
    except (TypeError, ValueError):
        return ""
    if not isinstance(parsed, dict):
        return ""
    fingerprint = parsed.get("request_fingerprint")
    return str(fingerprint) if isinstance(fingerprint, str) else ""


def _request_kind(value: object) -> str:
    """Extract a legacy request classification from projected metadata."""

    if not value:
        return ""
    try:
        parsed = safe_load_bounded_json(
            str(value),
            maximum_bytes=4_096,
            maximum_depth=4,
            maximum_nodes=32,
        )
    except (TypeError, ValueError):
        return ""
    if not isinstance(parsed, dict):
        return ""
    request_kind = str(parsed.get("request_kind") or "")
    return request_kind if request_kind in {"trivial", "nontrivial"} else ""


def _prepare_preflight_failure_receipt(
    value: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], str, str, str]:
    """Validate and encode one bounded failure receipt for a Store write."""

    projected = project_preflight_failure_receipt(
        default_preflight_failure_receipt() if value is None else value
    )
    if projected is None:
        raise ValueError("preflight failure receipt is malformed or unbounded")
    encoded_attempts = json.dumps(
        projected["provider_attempts"],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    if len(encoded_attempts.encode("utf-8")) > MAX_PREFLIGHT_FAILURE_PROVIDER_ATTEMPTS_BYTES:
        raise ValueError("preflight failure provider attempts exceed their durable bound")
    encoded_staffing = json.dumps(
        projected["staffing_reason_codes"],
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    encoded_hiring = json.dumps(
        projected["hiring_reason_codes"],
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    if any(
        len(encoded.encode("utf-8")) > MAX_PREFLIGHT_FAILURE_REASON_CODES_BYTES
        for encoded in (encoded_staffing, encoded_hiring)
    ):
        raise ValueError("preflight failure reason codes exceed their durable bound")
    return projected, encoded_attempts, encoded_staffing, encoded_hiring


def _decode_preflight_failure_receipt(row: Mapping[str, Any]) -> dict[str, Any]:
    """Decode one stored receipt without accepting unbounded JSON."""

    try:
        provider_attempts = safe_load_bounded_json(
            str(row["provider_attempts"]),
            maximum_bytes=MAX_PREFLIGHT_FAILURE_PROVIDER_ATTEMPTS_BYTES,
            maximum_depth=4,
            maximum_nodes=512,
        )
        staffing_reason_codes = safe_load_bounded_json(
            str(row["staffing_reason_codes"]),
            maximum_bytes=MAX_PREFLIGHT_FAILURE_REASON_CODES_BYTES,
            maximum_depth=2,
            maximum_nodes=64,
        )
        hiring_reason_codes = safe_load_bounded_json(
            str(row["hiring_reason_codes"]),
            maximum_bytes=MAX_PREFLIGHT_FAILURE_REASON_CODES_BYTES,
            maximum_depth=2,
            maximum_nodes=64,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError("preflight failure receipt failed integrity validation") from exc
    projected = project_preflight_failure_receipt(
        {
            "schema_version": PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
            "stage": row["stage"],
            "reason_code": row["reason_code"],
            "invariant_code": row["invariant_code"],
            "exception_category": row["exception_category"],
            "provider_attempts": provider_attempts,
            "staffing_reason_codes": staffing_reason_codes,
            "hiring_reason_codes": hiring_reason_codes,
        }
    )
    if projected is None:
        raise RuntimeError("preflight failure receipt failed integrity validation")
    return projected


def _project_turn_classification(value: object) -> dict[str, Any] | None:
    """Validate one content-free state-aware turn decision."""

    if not isinstance(value, Mapping):
        return None
    turn_kind = str(value.get("turn_kind") or "").strip()
    state_revision = str(value.get("state_revision") or "").strip()
    continuation_of = str(value.get("continuation_of") or "").strip()
    classifier_version = value.get("classifier_version")
    message_fingerprint = str(value.get("message_fingerprint") or "").strip()
    confidence = value.get("confidence")
    booleans = {
        field: value.get(field)
        for field in (
            "selection_required",
            "reroute_required",
            "execution_decision_required",
        )
    }
    if (
        turn_kind not in _TURN_KINDS
        or _DIGEST_PATTERN.fullmatch(state_revision) is None
        or isinstance(classifier_version, bool)
        or not isinstance(classifier_version, int)
        or not 1 <= classifier_version <= TURN_CLASSIFIER_VERSION
        or any(not isinstance(item, bool) for item in booleans.values())
        or (classifier_version >= 3 and _DIGEST_PATTERN.fullmatch(message_fingerprint) is None)
        or (message_fingerprint and _DIGEST_PATTERN.fullmatch(message_fingerprint) is None)
    ):
        return None
    try:
        normalized_continuation = validate_correlation_id(
            continuation_of,
            field="continuation_of",
            required=False,
        )
    except ValueError:
        return None
    decisions = (
        booleans["selection_required"],
        booleans["reroute_required"],
        booleans["execution_decision_required"],
    )
    allowed = {
        "acknowledgement": {(False, False, False), (True, True, True)},
        "conversation": (
            {(True, True, True), (False, False, False)}
            if classifier_version >= 4
            else {(True, True, True)}
        ),
        "control": {(False, False, False)},
        "continuation": {(True, False, True), (True, True, True)},
        "new_intent": {(True, True, True)},
        "revision": {(True, True, True)},
    }
    if decisions not in allowed[turn_kind] or (
        (turn_kind in {"continuation", "revision"}) != bool(normalized_continuation)
    ):
        return None
    raw_reasons = value.get("reason_codes")
    if not isinstance(raw_reasons, (list, tuple)) or len(raw_reasons) > 8:
        return None
    reasons: list[str] = []
    for raw_reason in raw_reasons:
        reason = str(raw_reason or "").strip()
        if not reason or len(reason) > 96 or re.fullmatch(r"[a-z][a-z0-9_.-]*", reason) is None:
            return None
        if reason not in reasons:
            reasons.append(reason)
    return {
        "turn_kind": turn_kind,
        **booleans,
        "continuation_of": normalized_continuation,
        "confidence": _bounded_finite_float(confidence),
        "reason_codes": reasons,
        "state_revision": state_revision,
        "classifier_version": classifier_version,
        "message_fingerprint": message_fingerprint,
    }


def _bounded_nonnegative_int(value: object, *, maximum: int) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, min(int(value), maximum))
    except (TypeError, ValueError, OverflowError):
        return 0


def _bounded_finite_float(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return max(-1_000_000.0, min(number, 1_000_000.0)) if math.isfinite(number) else 0.0


def _project_content_free_work_units(value: object) -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    confidence = raw.get("confidence", "")
    return {
        "delegate": bool(raw.get("delegate", False)),
        "count": _bounded_nonnegative_int(raw.get("count", 0), maximum=16),
        "confidence": str(confidence or "").strip()[:32],
        "source": str(raw.get("source") or "").strip()[:64],
    }


def _project_workforce_replay_fields(value: Mapping[str, Any]) -> dict[str, Any] | None:
    """Retain only the bounded workforce metadata required for exact replay."""

    from agency_runtime.core.activation_canary_contract import (
        CODEX_ACTIVATION_CANARY_ROUTE_SOURCE,
    )

    has_descriptors = "workforce_unit_descriptors" in value
    activation_canary = str(value.get("source") or "") == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
    if not has_descriptors and not activation_canary:
        return {}

    from agency_runtime.core.workforce.routing_projection import (
        project_workforce_unit_bindings,
        project_workforce_unit_descriptors,
    )

    projected: dict[str, Any] = {}
    if has_descriptors:
        descriptors = project_workforce_unit_descriptors(value.get("workforce_unit_descriptors"))
        if descriptors is None:
            return None
        projected["workforce_unit_descriptors"] = descriptors
    bindings = project_workforce_unit_bindings(value.get("workforce_unit_bindings"))
    if bindings is None:
        return None
    projected["workforce_unit_bindings"] = bindings
    return projected


def _project_recipe_routing(value: object, *, trace_id: str) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    safe_decision, safe_work_units, _source = project_routing_decision(value)
    # Providers are operational diagnostics and may include deployment names;
    # they are not required to deterministically rebuild prompt context.
    safe_decision.pop("provider", None)
    safe_decision["trace_id"] = trace_id
    safe_decision["work_units"] = _project_content_free_work_units(safe_work_units)
    workforce_fields = _project_workforce_replay_fields(value)
    if workforce_fields is None:
        return None
    safe_decision.update(workforce_fields)
    return safe_decision


def _project_specialist_refs(
    value: object,
    *,
    maximum: int = MAX_DURABLE_SPECIALIST_REFERENCES,
) -> list[dict[str, Any]] | None:
    if not isinstance(value, (list, tuple)) or len(value) > maximum:
        return None
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            return None
        slug = str(item.get("slug") or "").strip()
        version = str(item.get("version") or "").strip()
        content_hash = str(item.get("hash") or "").strip()
        if (
            not slug
            or len(slug.encode("utf-8", errors="surrogatepass")) > 128
            or slug in seen
            or is_resident_manager_slug(slug)
            or not is_valid_version_identity(version)
            or len(version.encode("utf-8", errors="surrogatepass")) > MAX_VERSION_IDENTITY_BYTES
            or not is_valid_version_identity(content_hash)
        ):
            return None
        raw_capabilities = item.get("capabilities")
        capabilities = (
            [
                str(capability or "").strip()[:64]
                for capability in raw_capabilities[:4]
                if str(capability or "").strip()
            ]
            if isinstance(raw_capabilities, (list, tuple))
            else []
        )
        result.append(
            {
                "slug": slug,
                "version": version,
                "hash": content_hash,
                "description": str(item.get("description") or "").strip()[:256],
                "capabilities": capabilities,
            }
        )
        seen.add(slug)
    return result


def _projection_digest(value: object) -> str:
    # Keep this import local: importing the selector package while Store mixins
    # initialize creates a cli_transport -> Store -> selector cycle.
    from agency_runtime.core.selector.receipt_projection import routing_projection_digest

    return routing_projection_digest(value)


def _project_continuation_guard(value: object) -> dict[str, Any] | None:
    """Validate the bounded source-state CAS carried by a v10 continuation."""

    if value is None:
        return None
    if not isinstance(value, Mapping) or value.get("guard_version") != _CONTINUATION_GUARD_VERSION:
        return None
    try:
        source_trace_id = validate_correlation_id(
            str(value.get("source_trace_id") or ""),
            field="source_trace_id",
        )
    except ValueError:
        return None
    source_turn_sequence = value.get("source_turn_sequence")
    source_evidence_revision = value.get("source_evidence_revision")
    source_roster_generation = value.get("source_roster_generation")
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item < minimum
        for item, minimum in (
            (source_turn_sequence, 1),
            (source_evidence_revision, 1),
            (source_roster_generation, 0),
        )
    ):
        return None
    digest_fields = (
        "source_recipe_digest",
        "source_routing_digest",
        "routing_fingerprint",
        "context_policy_fingerprint",
        "selection_digest",
        "delegation_digest",
    )
    digests = {field: str(value.get(field) or "").strip() for field in digest_fields}
    if any(_DIGEST_PATTERN.fullmatch(digest) is None for digest in digests.values()):
        return None
    return {
        "guard_version": _CONTINUATION_GUARD_VERSION,
        "source_trace_id": source_trace_id,
        "source_turn_sequence": source_turn_sequence,
        "source_evidence_revision": source_evidence_revision,
        "source_roster_generation": source_roster_generation,
        **digests,
    }


def _project_resident_manager_kernel(value: object) -> dict[str, Any] | None:
    """Project one bounded content-free resident-kernel identity."""

    if not isinstance(value, Mapping):
        return None
    version = value.get("version")
    content_hash = str(value.get("content_hash") or "").strip().casefold()
    raw_slugs = value.get("slugs")
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or not 1 <= version <= 1_000
        or _DIGEST_PATTERN.fullmatch(content_hash) is None
        or not isinstance(raw_slugs, list)
        or len(raw_slugs) != 2
    ):
        return None
    slugs = [str(slug or "").strip().casefold()[:128] for slug in raw_slugs]
    if any(not slug for slug in slugs) or len(set(slugs)) != len(slugs):
        return None
    return {"version": version, "content_hash": content_hash, "slugs": slugs}


def _project_preflight_recipe(
    value: object,
    *,
    session_id: str,
    trace_id: str,
) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    recipe_version = value.get("recipe_version")
    policy_fingerprint = str(value.get("policy_fingerprint") or "").strip()
    host = str(value.get("host") or "").strip().casefold()[:64]
    delivery_mode = str(value.get("delivery_mode") or "").strip().casefold()
    context_limit = value.get("context_limit")
    trivial = value.get("trivial")
    if (
        isinstance(recipe_version, bool)
        or not isinstance(recipe_version, int)
        or recipe_version not in SUPPORTED_PREFLIGHT_RECIPE_VERSIONS
        or _DIGEST_PATTERN.fullmatch(policy_fingerprint) is None
        or not host
        or delivery_mode not in {"direct", "isolated"}
        or isinstance(context_limit, bool)
        or not isinstance(context_limit, int)
        or not 256 <= context_limit <= 32_000
        or not isinstance(trivial, bool)
    ):
        return None
    refs = _project_specialist_refs(value.get("specialist_refs"))
    selection_refs = _project_specialist_refs(
        value.get("selection_refs", []),
        maximum=_MAX_SELECTION_REFS,
    )
    unit_assignment_agents = project_unit_assignment_agents(
        value.get("unit_assignment_agents", []),
        strict=True,
    )
    unit_agent_plan = _project_suggestions(
        value.get("unit_agent_plan", []),
        recipe_version=recipe_version if isinstance(recipe_version, int) else None,
    )
    routing = _project_recipe_routing(value.get("routing"), trace_id=trace_id)
    turn_classification = _project_turn_classification(value.get("turn_classification"))
    continuation_guard = _project_continuation_guard(value.get("continuation_guard"))
    roster_generation = value.get("roster_generation", 0)
    raw_resident_manager_kernel = value.get("resident_manager_kernel")
    resident_manager_kernel = _project_resident_manager_kernel(raw_resident_manager_kernel)
    raw_resident_manager_binding = value.get("resident_manager_binding")
    resident_manager_binding: dict[str, Any] | None = None
    if recipe_version >= 8:
        try:
            validated_binding = validate_resident_manager_binding(
                raw_resident_manager_binding,
                session_id=session_id,
            )
        except ValueError:
            validated_binding = None
        if validated_binding is not None:
            resident_manager_binding = validated_binding.as_dict()
    if (
        refs is None
        or selection_refs is None
        or unit_assignment_agents is None
        or unit_agent_plan is None
        or routing is None
        or isinstance(roster_generation, bool)
        or not isinstance(roster_generation, int)
        or roster_generation < 0
        or (recipe_version >= 10 and "roster_generation" not in value)
        or (recipe_version >= 10 and "selection_refs" not in value)
        or (value.get("continuation_guard") is not None and continuation_guard is None)
        or (recipe_version >= 6 and turn_classification is None)
        or (
            recipe_version == 7
            and not is_current_resident_manager_kernel_reference(resident_manager_kernel)
        )
        or (recipe_version < 7 and raw_resident_manager_kernel is not None)
        or (recipe_version < 8 and raw_resident_manager_binding is not None)
        or (
            recipe_version >= 8
            and (
                raw_resident_manager_kernel is not None
                or resident_manager_binding is None
                or resident_manager_binding["host"] != canonical_resident_manager_host(host)
            )
        )
    ):
        return None
    selection_slugs = {item["slug"] for item in selection_refs}
    required_selection_slugs = {
        str(slug) for slug in routing.get("selected_ids", []) if not is_resident_manager_slug(slug)
    }
    required_selection_slugs.update(item["recommended_agent"] for item in unit_agent_plan)
    if (
        (
            recipe_version >= 10
            and (
                any(item["slug"] not in selection_slugs for item in refs)
                or not required_selection_slugs.issubset(selection_slugs)
            )
        )
        or (
            continuation_guard is not None
            and (
                recipe_version < 10
                or turn_classification is None
                or turn_classification["turn_kind"] != "continuation"
                or turn_classification["continuation_of"] != continuation_guard["source_trace_id"]
                or routing.get("origin_trace_id") != continuation_guard["source_trace_id"]
            )
        )
        or (routing.get("continuation_reused") is True and continuation_guard is None)
    ):
        return None
    projected = {
        "recipe_version": recipe_version,
        "policy_fingerprint": policy_fingerprint,
        "session_id": session_id,
        "trace_id": trace_id,
        "host": host,
        "delivery_mode": delivery_mode,
        "context_limit": context_limit,
        "routing": routing,
        "specialist_refs": refs,
        "selection_refs": selection_refs,
        "unit_assignment_agents": unit_assignment_agents,
        "unit_agent_plan": unit_agent_plan,
        "trivial": trivial,
        "roster_size": _bounded_nonnegative_int(value.get("roster_size", 0), maximum=100_000),
        "roster_generation": roster_generation,
    }
    if turn_classification is not None:
        projected["turn_classification"] = turn_classification
    if resident_manager_kernel is not None:
        projected["resident_manager_kernel"] = resident_manager_kernel
    if resident_manager_binding is not None:
        projected["resident_manager_binding"] = resident_manager_binding
    if continuation_guard is not None:
        projected["continuation_guard"] = continuation_guard
    return projected


def _decode_preflight_recipe(
    value: object,
    *,
    session_id: str,
    trace_id: str,
) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        parsed = safe_load_bounded_json(
            str(value),
            maximum_bytes=_MAX_RECIPE_BYTES,
            maximum_depth=10,
            maximum_nodes=_MAX_RECIPE_NODES,
        )
    except (TypeError, ValueError):
        return None
    return _project_preflight_recipe(parsed, session_id=session_id, trace_id=trace_id)


def _preflight_clock(conn: Any, lease_seconds: int | None) -> tuple[str, str]:
    if lease_seconds is None:
        requested = MAX_HOOK_TIMEOUT_SECONDS
    elif isinstance(lease_seconds, bool):
        raise ValueError("preflight lease budget must be an integer")
    else:
        requested = int(lease_seconds)
    if not 1 <= requested <= MAX_HOOK_TIMEOUT_SECONDS:
        raise ValueError("preflight lease budget exceeds the supported hook timeout")
    effective = requested + math.ceil(HOOK_TIMEOUT_BUFFER_SECONDS)
    row = conn.execute(
        f"SELECT {STORE_CLOCK_SQL} AS now_value, "  # nosec B608
        "STRFTIME('%Y-%m-%dT%H:%M:%f000+00:00', 'NOW', ?) AS lease_expires_at",
        (f"+{effective} seconds",),
    ).fetchone()
    return str(row["now_value"]), str(row["lease_expires_at"])


def _project_suggestions(
    value: object,
    *,
    recipe_version: int | None = None,
) -> list[dict[str, Any]] | None:
    from agency_runtime.core.unit_assignment import project_unit_agent_plan

    projected = project_unit_agent_plan(
        value,
        allow_legacy=recipe_version is None or recipe_version < 11,
        require_current=recipe_version is not None and recipe_version >= 11,
    )
    return projected


def _project_routing_evidence(value: object, *, trace_id: str) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    query_hash = str(value.get("query_hash") or "").strip()
    context_fingerprint = str(value.get("context_fingerprint") or "").strip()
    if (
        _DIGEST_PATTERN.fullmatch(query_hash) is None
        or _DIGEST_PATTERN.fullmatch(context_fingerprint) is None
    ):
        return None
    safe_decision, safe_work_units, source = project_routing_decision(value)
    safe_decision.pop("provider", None)
    safe_decision["trace_id"] = trace_id
    safe_decision["query_hash"] = query_hash
    safe_decision["context_fingerprint"] = context_fingerprint
    safe_decision["work_units"] = _project_content_free_work_units(safe_work_units)
    workforce_fields = _project_workforce_replay_fields(value)
    if workforce_fields is None:
        return None
    safe_decision.update(workforce_fields)
    from agency_runtime.core.selector.receipt_projection import (
        project_model_receipt_attempts,
    )

    model_receipts = project_model_receipt_attempts(value.get("model_receipt_attempts"))
    if model_receipts is None:
        return None
    from agency_runtime.core.workforce.hiring import PendingHiringCommit

    pending_hiring = value.get("_pending_hiring_commits", [])
    if (
        not isinstance(pending_hiring, list)
        or len(pending_hiring) > 16
        or any(not isinstance(item, PendingHiringCommit) for item in pending_hiring)
    ):
        return None
    return {
        "query_hash": query_hash,
        "context_fingerprint": context_fingerprint,
        "source": source,
        "decision": safe_decision,
        "model_receipts": model_receipts,
        "pending_hiring_commits": list(pending_hiring),
    }


def _prepare_ready_evidence(
    *,
    session_id: str,
    trace_id: str,
    attempt_token: str,
    host: str,
    recipe: Mapping[str, Any],
    routing_evidence: Mapping[str, Any],
    suggestions: list[dict[str, Any]],
    specialist_refs: list[dict[str, Any]],
) -> _ReadyEvidence:
    normalized_session = validate_correlation_id(session_id, field="session_id")
    normalized_trace = validate_correlation_id(trace_id, field="trace_id")
    normalized_attempt = str(attempt_token or "").strip()
    if not normalized_attempt:
        raise ValueError("attempt_token is required")
    projected_refs = _project_specialist_refs(specialist_refs)
    if projected_refs is None:
        raise ValueError("specialist replay references are invalid or unbounded")
    projected_recipe = _project_preflight_recipe(
        recipe,
        session_id=normalized_session,
        trace_id=normalized_trace,
    )
    if projected_recipe is None or projected_recipe["specialist_refs"] != projected_refs:
        raise ValueError("preflight replay recipe is invalid or mismatched")
    normalized_host = str(host or "unknown").strip().casefold()[:64] or "unknown"
    if projected_recipe["host"] != normalized_host:
        raise ValueError("preflight ready host does not match its replay recipe")
    projected_suggestions = _project_suggestions(
        suggestions,
        recipe_version=int(projected_recipe["recipe_version"]),
    )
    if not isinstance(suggestions, list) or projected_suggestions is None:
        raise ValueError("preflight suggestions are invalid or unbounded")
    if projected_recipe["unit_agent_plan"] != projected_suggestions:
        raise ValueError("preflight unit-agent plan is invalid or mismatched")
    projected_routing = _project_routing_evidence(
        routing_evidence,
        trace_id=normalized_trace,
    )
    if projected_routing is None:
        raise ValueError("routing evidence requires bounded content-free digests")
    if projected_recipe["routing"] != projected_routing["decision"]:
        raise ValueError("preflight recipe and routing evidence do not match")
    for pending in projected_routing["pending_hiring_commits"]:
        case_arguments = pending.case_arguments
        if (
            str(case_arguments.get("session_id") or "") != normalized_session
            or str(case_arguments.get("trace_id") or "") != normalized_trace
        ):
            raise ValueError("pending hiring commit correlation does not match preflight")
    if projected_recipe["roster_size"] < len(projected_refs):
        raise ValueError("preflight roster size cannot be smaller than selected specialists")
    work_units = projected_recipe["routing"].get("work_units") or {}
    if projected_suggestions and (
        not work_units.get("delegate")
        or len(projected_suggestions) > int(work_units.get("count") or 0)
    ):
        raise ValueError("preflight suggestions do not match work-unit metadata")
    encoded_recipe = json.dumps(projected_recipe, sort_keys=True, separators=(",", ":"))
    if len(encoded_recipe.encode("utf-8")) > _MAX_RECIPE_BYTES:
        raise ValueError("preflight replay recipe exceeds the bounded store limit")
    return _ReadyEvidence(
        session_id=normalized_session,
        trace_id=normalized_trace,
        attempt_token=normalized_attempt,
        host=normalized_host,
        recipe=projected_recipe,
        encoded_recipe=encoded_recipe,
        delivery_mode=str(projected_recipe["delivery_mode"]),
        specialist_refs=projected_refs,
        suggestions=projected_suggestions,
        routing=projected_routing,
        model_receipts=[
            _normalize_receipt_ingress(
                {
                    "trace_id": normalized_trace,
                    "session_id": normalized_session,
                    "host": normalized_host,
                    "requested_model": attempt["requested_model"],
                    "model_group": attempt["model_group"],
                    "resolved_provider": attempt["provider_name"],
                    "resolved_model": attempt["actual_model"],
                    "attempted_fallbacks": ordinal,
                    "source": "wrapper",
                    "status": ("success" if attempt["status"] == "applied" else "failed"),
                },
                provenance=_ReceiptProvenance.GENERIC,
            )
            for ordinal, attempt in enumerate(projected_routing["model_receipts"])
        ],
        pending_hiring_commits=projected_routing["pending_hiring_commits"],
        resident_manager_binding=(
            dict(projected_recipe["resident_manager_binding"])
            if isinstance(projected_recipe.get("resident_manager_binding"), dict)
            else None
        ),
    )


def _project_codex_native_plan_scopes(
    evidence: _ReadyEvidence,
    value: object,
) -> list[tuple[CodexNativePlanScope, str]]:
    """Validate private scopes against the exact content-free ready recipe."""

    if not isinstance(value, list):
        raise ValueError("Codex native plan scopes must be a list")
    expected_required = bool(
        evidence.host == "codex"
        and evidence.delivery_mode == "isolated"
        and evidence.suggestions
        and evidence.recipe["routing"].get("continuation_reused") is not True
    )
    if not expected_required:
        if value:
            raise ValueError("Codex native plan scopes are not valid for this preflight")
        return []
    references = {item["slug"]: item for item in evidence.specialist_refs}
    suggestions = {item["work_unit_id"]: item for item in evidence.suggestions}
    if len(suggestions) != len(evidence.suggestions) or len(value) != len(suggestions):
        raise ValueError("Codex native plan scopes do not cover the exact plan")
    projected: list[tuple[CodexNativePlanScope, str]] = []
    seen: set[str] = set()
    for raw in value:
        scope = validate_codex_native_plan_scope(raw)
        suggestion = suggestions.get(scope.work_unit_id)
        reference = references.get(scope.specialist.slug)
        if suggestion is None or reference is None or scope.work_unit_id in seen:
            raise ValueError("Codex native plan scope identity does not match the ready plan")
        expected_evidence = build_native_child_evidence_contract(
            contract_id="agency-native-child-plan-v1",
            requirements=native_child_evidence_requirements(suggestion.get("required_evidence")),
        )
        if (
            suggestion.get("recommended_agent") != scope.specialist.slug
            or suggestion.get("goal_hash") != scope.goal_hash
            or tuple(suggestion.get("resource_hashes") or ()) != scope.resource_hashes
            or suggestion.get("mutation_scope") != scope.mutation_scope.mode
            or reference.get("version") != scope.specialist.version
            or reference.get("hash") != scope.specialist.content_hash
            or expected_evidence != scope.evidence_contract
        ):
            raise ValueError("Codex native plan scope does not match the ready plan")
        seen.add(scope.work_unit_id)
        projected.append((scope, serialize_codex_native_plan_scope(scope)))
    if seen != set(suggestions):
        raise ValueError("Codex native plan scopes do not cover the exact plan")
    return projected


def _commit_codex_native_plan_scopes(
    store: Any,
    conn: Any,
    evidence: _ReadyEvidence,
    scopes: list[tuple[CodexNativePlanScope, str]],
) -> None:
    """Insert or verify the exact private scope set inside the ready CAS."""

    rows = conn.execute(
        "SELECT session_id, trace_id, work_unit_id, scope_payload "
        "FROM codex_native_plan_scopes WHERE trace_id = ? ORDER BY work_unit_id",
        (evidence.trace_id,),
    ).fetchall()
    expected = {scope.work_unit_id: payload for scope, payload in scopes}
    if rows:
        observed: dict[str, str] = {}
        for row in rows:
            if (
                str(row["session_id"] or "") != evidence.session_id
                or str(row["trace_id"] or "") != evidence.trace_id
            ):
                raise RuntimeError("persisted Codex native plan scope correlation is invalid")
            payload = str(row["scope_payload"] or "")
            scope = deserialize_codex_native_plan_scope(payload)
            if scope.work_unit_id != str(row["work_unit_id"] or ""):
                raise RuntimeError("persisted Codex native plan scope identity is invalid")
            observed[scope.work_unit_id] = payload
        if observed != expected:
            raise RuntimeError("persisted Codex native plan scopes do not match the ready plan")
        return
    for scope, payload in scopes:
        conn.execute(
            "INSERT INTO codex_native_plan_scopes "
            "(id, session_id, trace_id, work_unit_id, scope_payload, created_at) "
            f"VALUES (?, ?, ?, ?, ?, {STORE_CLOCK_SQL})",  # nosec B608
            (
                store._uuid(),
                evidence.session_id,
                evidence.trace_id,
                scope.work_unit_id,
                payload,
            ),
        )


def _commit_pending_hiring_evidence(
    store: Any,
    conn: Any,
    evidence: _ReadyEvidence,
) -> None:
    """Commit validated hiring mutations and their receipts in the ready transaction."""

    if not evidence.pending_hiring_commits:
        return
    from agency_runtime.core.workforce.hiring import (
        commit_pending_contractor_hiring,
    )

    bound_store, transaction_state = _ready_transaction_store(store, conn)
    for pending in evidence.pending_hiring_commits:
        commit_pending_contractor_hiring(pending, store=bound_store)
        for fallback_count, receipt in enumerate(
            pending.case_arguments["model_evidence"]["receipts"]
        ):
            bound_store.record_model_receipt(
                trace_id=evidence.trace_id,
                session_id=evidence.session_id,
                host=evidence.host,
                requested_model=str(receipt.get("requested_model") or ""),
                resolved_provider=str(receipt.get("provider") or ""),
                resolved_model=str(receipt.get("actual_model") or ""),
                attempted_fallbacks=fallback_count,
                source="wrapper",
                status="success",
            )
    if transaction_state.rollback_requested:
        raise RuntimeError("pending hiring commit requested rollback")


_CONTINUATION_ROUTING_FIELDS = (
    "selected_ids",
    "semantic_ids",
    "companion_actions",
    "companion_ids",
    "available_companion_ids",
    "unavailable_companion_ids",
    "fallback_companion_ids",
    "available_fallback_companion_ids",
    "unavailable_fallback_companion_ids",
    "fallback_considered",
    "fallback_applied",
    "confidence",
    "top_score",
    "candidate_count",
    "work_units",
    "workforce_unit_descriptors",
    "workforce_unit_bindings",
)


def _delegation_component(conn: Any, trace_id: str) -> tuple[list[dict[str, Any]], str, bool]:
    rows = [
        dict(row)
        for row in conn.execute(
            "SELECT id, work_unit_id, recommended_agent, status, backend, "
            "executed_worker_kind, executed_worker_id, native_run_id, "
            "retrieved_specialist_slug, retrieved_specialist_version, "
            "retrieved_specialist_prompt_hash, activation_receipt_id, skip_reason, "
            "error, started_at, completed_at FROM delegation_events "
            "WHERE trace_id = ? ORDER BY work_unit_id, id",
            (trace_id,),
        ).fetchall()
    ]
    pristine = all(
        row["status"] == "suggested"
        and not any(
            row.get(field)
            for field in (
                "backend",
                "executed_worker_kind",
                "executed_worker_id",
                "native_run_id",
                "retrieved_specialist_slug",
                "retrieved_specialist_version",
                "retrieved_specialist_prompt_hash",
                "activation_receipt_id",
                "skip_reason",
                "error",
                "completed_at",
            )
        )
        for row in rows
    )
    activation_count = int(
        conn.execute(
            "SELECT COUNT(*) AS count FROM delegation_activation_receipts WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()["count"]
    )
    worker_count = int(
        conn.execute(
            "SELECT COUNT(*) AS count FROM worker_runs AS worker "
            "JOIN delegation_events AS event ON event.id = worker.delegation_event_id "
            "WHERE event.trace_id = ?",
            (trace_id,),
        ).fetchone()["count"]
    )
    return (
        rows,
        _projection_digest(rows),
        bool(pristine and not activation_count and not worker_count),
    )


def _selection_refs_match_active(
    conn: Any,
    selection_refs: list[dict[str, Any]],
) -> bool:
    if not selection_refs:
        return True
    rows = conn.execute(
        "SELECT agent_slug, version, hash FROM agent_active WHERE agent_slug IN ("
        + ",".join("?" for _item in selection_refs)
        + ")",
        tuple(item["slug"] for item in selection_refs),
    ).fetchall()
    active = {str(row["agent_slug"]): (str(row["version"]), str(row["hash"])) for row in rows}
    return all(
        active.get(item["slug"]) == (item["version"], item["hash"]) for item in selection_refs
    )


def _routing_component_matches(
    conn: Any,
    *,
    session_id: str,
    trace_id: str,
    routing: dict[str, Any],
) -> bool:
    rows = conn.execute(
        "SELECT query_hash, context_fingerprint, source, decision "
        "FROM routing_decisions WHERE session_id = ? AND trace_id = ? ORDER BY id",
        (session_id, trace_id),
    ).fetchall()
    if len(rows) != 1:
        return False
    row = rows[0]
    try:
        decision = safe_load_bounded_json(
            str(row["decision"] or ""),
            maximum_bytes=64_000,
            maximum_depth=8,
            maximum_nodes=_MAX_RECIPE_NODES,
        )
    except (TypeError, ValueError):
        return False
    if not isinstance(decision, dict):
        return False
    projected = _project_routing_evidence(
        {
            **decision,
            "query_hash": str(row["query_hash"] or ""),
            "context_fingerprint": str(row["context_fingerprint"] or ""),
        },
        trace_id=trace_id,
    )
    return bool(
        projected is not None
        and projected["decision"] == routing
        and projected["source"] == str(row["source"] or "")
    )


def _continuation_source_snapshot(
    conn: Any,
    *,
    session_id: str,
    trace_id: str,
    source_trace_id: str,
    host: str,
    routing_fingerprint: str,
    context_policy_fingerprint: str,
    roster_generation: int,
) -> dict[str, Any] | None:
    target = conn.execute(
        "SELECT turn_sequence FROM runs WHERE session_id = ? AND trace_id = ? "
        "AND status = 'active'",
        (session_id, trace_id),
    ).fetchone()
    source = conn.execute(
        "SELECT session_id, host, status, preflight_state, preflight_result, "
        "evidence_revision, turn_sequence FROM runs WHERE trace_id = ?",
        (source_trace_id,),
    ).fetchone()
    counter = conn.execute(
        "SELECT value FROM store_counters WHERE name = 'roster-generation'"
    ).fetchone()
    if (
        target is None
        or source is None
        or counter is None
        or str(source["session_id"] or "") != session_id
        or (str(source["host"] or "unknown").strip().casefold()[:64] or "unknown") != host
        or str(source["status"] or "") not in {"active", "evidence_only", "abandoned"}
        or str(source["preflight_state"] or "") != "ready"
        or int(source["turn_sequence"] or 0) + 1 != int(target["turn_sequence"] or 0)
        or int(counter["value"]) != roster_generation
    ):
        return None
    raw_recipe = str(source["preflight_result"] or "")
    recipe = _decode_preflight_recipe(
        raw_recipe,
        session_id=session_id,
        trace_id=source_trace_id,
    )
    if (
        not isinstance(recipe, dict)
        or recipe.get("recipe_version") != PREFLIGHT_REPLAY_RECIPE_VERSION
        or recipe.get("policy_fingerprint") != context_policy_fingerprint
        or recipe.get("roster_generation") != roster_generation
        or recipe.get("routing", {}).get("context_fingerprint") != routing_fingerprint
        or recipe.get("routing", {}).get("continuation_resolution_required") is True
    ):
        return None
    selection_refs = recipe.get("selection_refs")
    if not isinstance(selection_refs, list) or not _selection_refs_match_active(
        conn, selection_refs
    ):
        return None
    routing = recipe.get("routing")
    if not isinstance(routing, dict) or not _routing_component_matches(
        conn,
        session_id=session_id,
        trace_id=source_trace_id,
        routing=routing,
    ):
        return None
    delegation_rows, delegation_digest, pristine = _delegation_component(conn, source_trace_id)
    if not pristine:
        return None
    plan = recipe.get("unit_agent_plan")
    if not isinstance(plan, list) or sorted(
        (item["work_unit_id"], item["recommended_agent"]) for item in plan
    ) != sorted(
        (str(row["work_unit_id"]), str(row["recommended_agent"])) for row in delegation_rows
    ):
        return None
    guard = {
        "guard_version": _CONTINUATION_GUARD_VERSION,
        "source_trace_id": source_trace_id,
        "source_turn_sequence": int(source["turn_sequence"]),
        "source_evidence_revision": int(source["evidence_revision"]),
        "source_roster_generation": roster_generation,
        "source_recipe_digest": sha256(raw_recipe.encode("utf-8")).hexdigest(),
        "source_routing_digest": _projection_digest(routing),
        "routing_fingerprint": routing_fingerprint,
        "context_policy_fingerprint": context_policy_fingerprint,
        "selection_digest": _projection_digest(selection_refs),
        "delegation_digest": delegation_digest,
    }
    return {"recipe": recipe, "guard": guard}


def _continuation_guard_matches(
    conn: Any,
    recipe: dict[str, Any],
) -> bool:
    from agency_runtime.core.selector.receipt_projection import (
        normalize_durable_routing_receipt,
    )

    guard = recipe.get("continuation_guard")
    classification = recipe.get("turn_classification")
    routing = recipe.get("routing")
    if (
        not isinstance(guard, dict)
        or not isinstance(classification, dict)
        or not isinstance(routing, dict)
    ):
        return False
    snapshot = _continuation_source_snapshot(
        conn,
        session_id=str(recipe["session_id"]),
        trace_id=str(recipe["trace_id"]),
        source_trace_id=str(guard["source_trace_id"]),
        host=str(recipe["host"]),
        routing_fingerprint=str(guard["routing_fingerprint"]),
        context_policy_fingerprint=str(guard["context_policy_fingerprint"]),
        roster_generation=int(guard["source_roster_generation"]),
    )
    if snapshot is None or snapshot["guard"] != guard:
        return False
    source_recipe = snapshot["recipe"]
    source_routing = source_recipe["routing"]
    source_receipt = normalize_durable_routing_receipt(source_routing.get("routing_receipt"))
    target_receipt = normalize_durable_routing_receipt(routing.get("routing_receipt"))
    receipt_matches = bool(
        target_receipt is not None
        and (
            source_receipt is None
            or target_receipt.get("origin_receipt_digest") == _projection_digest(source_receipt)
        )
    )
    return bool(
        classification.get("continuation_of") == guard["source_trace_id"]
        and routing.get("continuation_reused") is True
        and routing.get("origin_trace_id") == guard["source_trace_id"]
        and routing.get("origin_query_hash") == source_routing.get("query_hash")
        and routing.get("origin_context_fingerprint") == source_routing.get("context_fingerprint")
        and receipt_matches
        and all(
            routing.get(field) == source_routing.get(field)
            for field in _CONTINUATION_ROUTING_FIELDS
        )
        and recipe.get("specialist_refs") == source_recipe.get("specialist_refs")
        and recipe.get("selection_refs") == source_recipe.get("selection_refs")
        and recipe.get("unit_assignment_agents") == source_recipe.get("unit_assignment_agents")
        and recipe.get("unit_agent_plan") == source_recipe.get("unit_agent_plan")
    )


class PreflightStoreMixin(ResidentManagerBindingStoreMixin):
    """Durable exact-turn preflight lifecycle composed into the Store."""

    def resolve_durable_continuation(
        self,
        *,
        session_id: str,
        trace_id: str,
        source_trace_id: str,
        host: str,
        routing_fingerprint: str,
        context_policy_fingerprint: str,
        roster_generation: int,
    ) -> dict[str, Any] | None:
        """Resolve one immediate v10 source without reading prompt or task bodies."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_source = validate_correlation_id(
            source_trace_id,
            field="source_trace_id",
        )
        normalized_host = str(host or "unknown").strip().casefold()[:64] or "unknown"
        if (
            _DIGEST_PATTERN.fullmatch(str(routing_fingerprint or "")) is None
            or _DIGEST_PATTERN.fullmatch(str(context_policy_fingerprint or "")) is None
            or isinstance(roster_generation, bool)
            or not isinstance(roster_generation, int)
            or roster_generation < 0
        ):
            return None
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            snapshot = _continuation_source_snapshot(
                conn,
                session_id=normalized_session,
                trace_id=normalized_trace,
                source_trace_id=normalized_source,
                host=normalized_host,
                routing_fingerprint=routing_fingerprint,
                context_policy_fingerprint=context_policy_fingerprint,
                roster_generation=roster_generation,
            )
            conn.commit()
            return snapshot
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _preflight_lifecycle_result(
        *,
        outcome: str,
        trace_id: str,
        attempt_token: str = "",
        lease_expires_at: str = "",
    ) -> dict[str, str]:
        return {
            "outcome": outcome,
            "trace_id": trace_id,
            "attempt_token": attempt_token,
            "lease_expires_at": lease_expires_at,
        }

    def _insert_preflight_attempt(
        self,
        conn: Any,
        request: _PreflightRequest,
        *,
        now_value: str,
        lease_expires_at: str,
    ) -> dict[str, str]:
        if request.reservation_token:
            return self._preflight_lifecycle_result(
                outcome="stale_reservation",
                trace_id=request.trace_id,
            )
        self._assert_trace_not_retired(conn, request.trace_id)
        attempt_token = self._uuid()
        conn.execute(
            "INSERT INTO runs "
            "(id, trace_id, session_id, host, started_at, last_activity_at, "
            "status, user_message, metadata, preflight_attempt_token, "
            "preflight_state, preflight_lease_expires_at, "
            "preflight_request_fingerprint, preflight_request_kind, "
            "preflight_result) "
            "VALUES (?, ?, ?, ?, ?, ?, "
            "'active', ?, ?, ?, 'in_progress', ?, ?, ?, '')",
            (
                self._uuid(),
                request.trace_id,
                request.session_id,
                request.host,
                now_value,
                now_value,
                request.user_message,
                request.metadata,
                attempt_token,
                lease_expires_at,
                request.fingerprint,
                request.request_kind,
            ),
        )
        return self._preflight_lifecycle_result(
            outcome="started",
            trace_id=request.trace_id,
            attempt_token=attempt_token,
            lease_expires_at=lease_expires_at,
        )

    def _promote_preflight_reservation(
        self,
        conn: Any,
        run: Any,
        request: _PreflightRequest,
        *,
        state: str,
        stored_reservation: str,
        now_value: str,
        lease_expires_at: str,
    ) -> dict[str, str]:
        if state != "reserved" or not stored_reservation:
            return self._preflight_lifecycle_result(
                outcome="stale_reservation",
                trace_id=request.trace_id,
            )
        attempt_token = self._uuid()
        promoted = conn.execute(
            "UPDATE runs SET status = 'active', host = ?, user_message = ?, "
            "metadata = ?, preflight_attempt_token = ?, "
            "preflight_state = 'in_progress', preflight_lease_expires_at = ?, "
            "preflight_request_fingerprint = ?, preflight_request_kind = ?, "
            "preflight_result = '', last_activity_at = ? "
            "WHERE id = ? AND status = 'evidence_only' "
            "AND preflight_state = 'reserved' AND reservation_token = ?",
            (
                request.host,
                request.user_message,
                request.metadata,
                attempt_token,
                lease_expires_at,
                request.fingerprint,
                request.request_kind,
                now_value,
                run["id"],
                stored_reservation,
            ),
        )
        if promoted.rowcount != 1:
            raise RuntimeError("preflight reservation promotion lost atomicity")
        return self._preflight_lifecycle_result(
            outcome="started",
            trace_id=request.trace_id,
            attempt_token=attempt_token,
            lease_expires_at=lease_expires_at,
        )

    def _start_uninitialized_preflight(
        self,
        conn: Any,
        run: Any,
        request: _PreflightRequest,
        *,
        stored_fingerprint: str,
        stored_kind: str,
        now_value: str,
        lease_expires_at: str,
    ) -> dict[str, str]:
        if (stored_fingerprint and stored_fingerprint != request.fingerprint) or (
            stored_kind and stored_kind != request.request_kind
        ):
            return self._preflight_lifecycle_result(
                outcome="conflict",
                trace_id=request.trace_id,
            )
        attempt_token = self._uuid()
        conn.execute(
            "UPDATE runs SET host = ?, user_message = ?, metadata = ?, "
            "preflight_attempt_token = ?, preflight_state = 'in_progress', "
            "preflight_lease_expires_at = ?, preflight_request_fingerprint = ?, "
            "preflight_request_kind = ?, preflight_result = '', last_activity_at = ? "
            "WHERE id = ?",
            (
                request.host,
                request.user_message,
                request.metadata,
                attempt_token,
                lease_expires_at,
                request.fingerprint,
                request.request_kind,
                now_value,
                run["id"],
            ),
        )
        return self._preflight_lifecycle_result(
            outcome="started",
            trace_id=request.trace_id,
            attempt_token=attempt_token,
            lease_expires_at=lease_expires_at,
        )

    def _recover_expired_preflight(
        self,
        conn: Any,
        run: Any,
        request: _PreflightRequest,
        *,
        prior_attempt_token: str,
        now_value: str,
        lease_expires_at: str,
    ) -> dict[str, str]:
        conn.execute(
            "DELETE FROM worker_runs WHERE delegation_event_id IN "
            "(SELECT id FROM delegation_events WHERE trace_id = ?)",
            (request.trace_id,),
        )
        for table in (
            "delegation_activation_receipts",
            "delegation_events",
            "routing_decisions",
            "specialists_loaded",
            "skills_loaded",
            "model_receipts",
            "finalization_events",
        ):
            conn.execute(
                f"DELETE FROM {table} WHERE trace_id = ?",  # nosec B608
                (request.trace_id,),
            )
        recovered_token = self._uuid()
        recovered = conn.execute(
            "UPDATE runs SET preflight_attempt_token = ?, "
            "preflight_state = 'in_progress', preflight_lease_expires_at = ?, "
            "preflight_result = '', last_activity_at = ? "
            "WHERE id = ? AND status = 'active' AND preflight_state = 'in_progress' "
            "AND preflight_attempt_token = ? AND preflight_lease_expires_at < ?",
            (
                recovered_token,
                lease_expires_at,
                now_value,
                run["id"],
                prior_attempt_token,
                now_value,
            ),
        )
        if recovered.rowcount != 1:
            raise RuntimeError("expired preflight recovery lost atomicity")
        return self._preflight_lifecycle_result(
            outcome="recovered_started",
            trace_id=request.trace_id,
            attempt_token=recovered_token,
            lease_expires_at=lease_expires_at,
        )

    def _reuse_active_preflight(
        self,
        conn: Any,
        run: Any,
        request: _PreflightRequest,
        *,
        state: str,
        stored_reservation: str,
        now_value: str,
        lease_expires_at: str,
    ) -> dict[str, str]:
        stored_fingerprint = str(
            run["preflight_request_fingerprint"] or ""
        ) or _request_fingerprint(run["metadata"])
        stored_kind = str(run["preflight_request_kind"] or "") or _request_kind(run["metadata"])
        if state == "" and not stored_reservation and not request.reservation_token:
            return self._start_uninitialized_preflight(
                conn,
                run,
                request,
                stored_fingerprint=stored_fingerprint,
                stored_kind=stored_kind,
                now_value=now_value,
                lease_expires_at=lease_expires_at,
            )
        if stored_fingerprint != request.fingerprint or stored_kind != request.request_kind:
            return self._preflight_lifecycle_result(
                outcome="conflict",
                trace_id=request.trace_id,
            )
        attempt_token = str(run["preflight_attempt_token"] or "")
        if state == "ready" and attempt_token:
            recipe = _decode_preflight_recipe(
                run["preflight_result"],
                session_id=request.session_id,
                trace_id=request.trace_id,
            )
            if recipe is not None:
                conn.execute(
                    f"UPDATE runs SET last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                    "WHERE id = ?",
                    (run["id"],),
                )
            return self._preflight_lifecycle_result(
                outcome="reused_ready" if recipe is not None else "conflict",
                trace_id=request.trace_id,
                attempt_token=attempt_token if recipe is not None else "",
            )
        if state != "in_progress" or not attempt_token:
            return self._preflight_lifecycle_result(
                outcome="conflict",
                trace_id=request.trace_id,
            )
        if str(run["preflight_lease_expires_at"] or "") >= now_value:
            conn.execute(
                f"UPDATE runs SET last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                "WHERE id = ?",
                (run["id"],),
            )
            return self._preflight_lifecycle_result(
                outcome="reused_in_progress",
                trace_id=request.trace_id,
                attempt_token=attempt_token,
                lease_expires_at=str(run["preflight_lease_expires_at"] or ""),
            )
        return self._recover_expired_preflight(
            conn,
            run,
            request,
            prior_attempt_token=attempt_token,
            now_value=now_value,
            lease_expires_at=lease_expires_at,
        )

    def _begin_existing_preflight(
        self,
        conn: Any,
        run: Any,
        request: _PreflightRequest,
        *,
        now_value: str,
        lease_expires_at: str,
    ) -> dict[str, str]:
        if str(run["session_id"] or "") != request.session_id:
            return self._preflight_lifecycle_result(
                outcome="conflict",
                trace_id=request.trace_id,
            )
        status = str(run["status"] or "")
        state = str(run["preflight_state"] or "")
        stored_reservation = str(run["reservation_token"] or "")
        if status not in {"active", "evidence_only"}:
            return self._preflight_lifecycle_result(
                outcome="terminal",
                trace_id=request.trace_id,
            )
        if stored_reservation and request.reservation_token != stored_reservation:
            return self._preflight_lifecycle_result(
                outcome="stale_reservation",
                trace_id=request.trace_id,
            )
        if status == "evidence_only":
            return self._promote_preflight_reservation(
                conn,
                run,
                request,
                state=state,
                stored_reservation=stored_reservation,
                now_value=now_value,
                lease_expires_at=lease_expires_at,
            )
        return self._reuse_active_preflight(
            conn,
            run,
            request,
            state=state,
            stored_reservation=stored_reservation,
            now_value=now_value,
            lease_expires_at=lease_expires_at,
        )

    def begin_preflight_attempt(
        self,
        *,
        session_id: str,
        trace_id: str,
        reservation_token: str = "",
        request_fingerprint: str,
        request_kind: str,
        host: str = "unknown",
        user_message: str = "",
        lease_seconds: int | None = None,
        turn_classification: Mapping[str, Any] | None = None,
    ) -> dict[str, str]:
        """Acquire or observe one fenced preflight owner using SQLite time."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_fingerprint = str(request_fingerprint or "").strip()
        normalized_kind = str(request_kind or "").strip()
        if not normalized_session or not normalized_trace:
            raise ValueError("session_id and trace_id are required for preflight")
        if _DIGEST_PATTERN.fullmatch(normalized_fingerprint) is None:
            raise ValueError("request_fingerprint must be a lowercase SHA-256 digest")
        if normalized_kind not in {"trivial", "nontrivial"}:
            raise ValueError("request_kind must be trivial or nontrivial")
        projected_turn = (
            _project_turn_classification(turn_classification)
            if turn_classification is not None
            else None
        )
        if turn_classification is not None and projected_turn is None:
            raise ValueError("turn_classification is invalid")
        captured_message = (
            redact_sensitive_text(user_message, _RUN_CONTENT_LIMIT)
            if self._capture_content_enabled()
            else ""
        )
        request = _PreflightRequest(
            session_id=normalized_session,
            trace_id=normalized_trace,
            reservation_token=str(reservation_token or "").strip(),
            fingerprint=normalized_fingerprint,
            request_kind=normalized_kind,
            host=str(host or "unknown").strip()[:64] or "unknown",
            user_message=captured_message,
            metadata=project_run_metadata(
                {
                    "source": "preflight_attempt",
                    "request_fingerprint": normalized_fingerprint,
                    "request_kind": normalized_kind,
                    **(
                        {
                            "turn_kind": projected_turn["turn_kind"],
                            "selection_required": projected_turn["selection_required"],
                            "reroute_required": projected_turn["reroute_required"],
                            "execution_decision_required": projected_turn[
                                "execution_decision_required"
                            ],
                            "continuation_of": projected_turn["continuation_of"],
                            "state_revision": projected_turn["state_revision"],
                            "classifier_version": projected_turn["classifier_version"],
                        }
                        if projected_turn is not None
                        else {}
                    ),
                }
            ),
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            now_value, lease_expires_at = _preflight_clock(conn, lease_seconds)
            run = conn.execute(
                "SELECT * FROM runs WHERE trace_id = ?",
                (request.trace_id,),
            ).fetchone()
            if run is None:
                result = self._insert_preflight_attempt(
                    conn,
                    request,
                    now_value=now_value,
                    lease_expires_at=lease_expires_at,
                )
            else:
                result = self._begin_existing_preflight(
                    conn,
                    run,
                    request,
                    now_value=now_value,
                    lease_expires_at=lease_expires_at,
                )
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def observe_preflight_attempt(
        self,
        session_id: str,
        trace_id: str,
        attempt_token: str,
    ) -> dict[str, Any] | None:
        """Observe one traced attempt without hiding terminal or fenced state."""

        if not session_id or not trace_id or not attempt_token:
            return None
        session_id = validate_correlation_id(session_id, field="session_id")
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT status, preflight_state, preflight_attempt_token, "
                "preflight_result FROM runs WHERE session_id = ? AND trace_id = ?",
                (session_id, trace_id),
            ).fetchone()
            if row is None:
                return None
            state = str(row["preflight_state"] or "")
            attempt_matches = str(row["preflight_attempt_token"] or "") == attempt_token
            recipe = (
                _decode_preflight_recipe(
                    row["preflight_result"],
                    session_id=session_id,
                    trace_id=trace_id,
                )
                if attempt_matches and str(row["status"] or "") == "active" and state == "ready"
                else None
            )
            return {
                "run_status": str(row["status"] or ""),
                "preflight_state": state,
                "attempt_matches": attempt_matches,
                "recipe": recipe,
            }
        finally:
            conn.close()

    def get_ready_preflight_result(
        self,
        session_id: str,
        trace_id: str,
        attempt_token: str,
    ) -> dict[str, Any] | None:
        observation = self.observe_preflight_attempt(session_id, trace_id, attempt_token)
        if (
            observation is None
            or observation["run_status"] != "active"
            or observation["preflight_state"] != "ready"
            or observation["attempt_matches"] is not True
        ):
            return None
        recipe = observation.get("recipe")
        return dict(recipe) if isinstance(recipe, dict) else None

    def get_ready_routing_receipt(
        self,
        session_id: str,
        trace_id: str,
        *,
        evidence_revision: int,
    ) -> dict[str, Any] | None:
        """Read one ready receipt under the completion snapshot's exact revision."""
        from agency_runtime.core.selector.receipt_projection import (
            normalize_durable_routing_receipt,
        )

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        if (
            isinstance(evidence_revision, bool)
            or not isinstance(evidence_revision, int)
            or evidence_revision <= 0
        ):
            raise ValueError("evidence_revision must be a positive integer")
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            row = conn.execute(
                "SELECT status, preflight_state, preflight_result, evidence_revision "
                "FROM runs WHERE session_id = ? AND trace_id = ?",
                (normalized_session, normalized_trace),
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            if (
                str(row["status"] or "") not in {"active", "evidence_only"}
                or str(row["preflight_state"] or "") != "ready"
                or int(row["evidence_revision"] or 0) != evidence_revision
            ):
                conn.commit()
                return None
            recipe = _decode_preflight_recipe(
                row["preflight_result"],
                session_id=normalized_session,
                trace_id=normalized_trace,
            )
            if recipe is None:
                raise RuntimeError("ready preflight recipe failed integrity validation")
            routing = recipe.get("routing")
            if not isinstance(routing, dict) or not _routing_component_matches(
                conn,
                session_id=normalized_session,
                trace_id=normalized_trace,
                routing=routing,
            ):
                raise RuntimeError("ready routing receipt failed integrity validation")
            receipt = normalize_durable_routing_receipt(routing.get("routing_receipt"))
            conn.commit()
            return receipt
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_preflight_failure_receipt(
        self,
        session_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        """Read the immutable content-free failure receipt for one exact turn."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT id, session_id, trace_id, host, stage, reason_code, "
                "invariant_code, exception_category, provider_attempts, staffing_reason_codes, "
                "hiring_reason_codes, recorded_at "
                "FROM preflight_failure_receipts WHERE session_id = ? AND trace_id = ?",
                (normalized_session, normalized_trace),
            ).fetchone()
            if row is None:
                return None
            return {**dict(row), **_decode_preflight_failure_receipt(row)}
        finally:
            conn.close()

    def fail_preflight_attempt(
        self,
        *,
        session_id: str,
        trace_id: str,
        attempt_token: str,
        status: str = "preflight_failed",
        failure_receipt: Mapping[str, Any] | None = None,
    ) -> bool:
        session_id = validate_correlation_id(session_id, field="session_id")
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        normalized_status = str(status or "").strip()
        if normalized_status in {"", "active", "evidence_only"}:
            raise ValueError("preflight failure requires a terminal status")
        projected_failure: tuple[dict[str, Any], str, str, str] | None = None
        if normalized_status == "preflight_failed":
            projected_failure = _prepare_preflight_failure_receipt(failure_receipt)
        elif failure_receipt is not None:
            raise ValueError("failure_receipt requires preflight_failed status")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            now_value = str(
                conn.execute(
                    f"SELECT {STORE_CLOCK_SQL} AS now_value"  # nosec B608
                ).fetchone()["now_value"]
            )
            closed = conn.execute(
                "UPDATE runs SET status = ?, ended_at = COALESCE(ended_at, ?), "
                "preflight_state = '', preflight_attempt_token = NULL, "
                "preflight_lease_expires_at = '', preflight_result = '', "
                f"last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                "WHERE session_id = ? AND trace_id = ? AND status = 'active' "
                "AND preflight_state = 'in_progress' AND preflight_attempt_token = ? "
                "AND preflight_lease_expires_at >= ?",
                (
                    normalized_status,
                    now_value,
                    session_id,
                    trace_id,
                    attempt_token,
                    now_value,
                ),
            )
            if closed.rowcount:
                if projected_failure is not None:
                    receipt, encoded_attempts, encoded_staffing, encoded_hiring = projected_failure
                    inserted = conn.execute(
                        "INSERT INTO preflight_failure_receipts "
                        "(id, session_id, trace_id, host, stage, reason_code, invariant_code, "
                        "exception_category, provider_attempts, staffing_reason_codes, "
                        "hiring_reason_codes, recorded_at) "
                        "SELECT ?, session_id, trace_id, host, ?, ?, ?, ?, ?, ?, ?, "
                        f"{STORE_CLOCK_SQL} FROM runs "  # nosec B608
                        "WHERE session_id = ? AND trace_id = ? AND status = 'preflight_failed'",
                        (
                            self._uuid(),
                            receipt["stage"],
                            receipt["reason_code"],
                            receipt["invariant_code"],
                            receipt["exception_category"],
                            encoded_attempts,
                            encoded_staffing,
                            encoded_hiring,
                            session_id,
                            trace_id,
                        ),
                    )
                    if inserted.rowcount != 1:
                        raise RuntimeError("preflight failure receipt lost turn correlation")
                conn.execute(
                    "UPDATE specialists_loaded SET expired_at = ? "
                    "WHERE session_id = ? AND trace_id = ? AND expired_at IS NULL",
                    (now_value, session_id, trace_id),
                )
            conn.commit()
            return closed.rowcount == 1
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def abandon_preflight_reservation(
        self,
        *,
        session_id: str,
        trace_id: str,
        reservation_token: str,
        status: str = "preflight_skipped",
        failure_receipt: Mapping[str, Any] | None = None,
    ) -> bool:
        session_id = validate_correlation_id(session_id, field="session_id")
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        normalized_status = str(status or "").strip()
        if normalized_status not in {"preflight_skipped", "preflight_failed"}:
            raise ValueError("reservation abandonment requires a preflight terminal status")
        projected_failure: tuple[dict[str, Any], str, str, str] | None = None
        if normalized_status == "preflight_failed":
            projected_failure = _prepare_preflight_failure_receipt(failure_receipt)
        elif failure_receipt is not None:
            raise ValueError("failure_receipt requires preflight_failed status")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            now_value = str(
                conn.execute(
                    f"SELECT {STORE_CLOCK_SQL} AS now_value"  # nosec B608
                ).fetchone()["now_value"]
            )
            closed = conn.execute(
                "UPDATE runs SET status = ?, ended_at = COALESCE(ended_at, ?), "
                "reservation_token = NULL, preflight_state = '', "
                "preflight_lease_expires_at = '', "
                f"last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                "WHERE session_id = ? AND trace_id = ? AND status = 'evidence_only' "
                "AND preflight_state = 'reserved' AND reservation_token = ?",
                (
                    normalized_status,
                    now_value,
                    session_id,
                    trace_id,
                    reservation_token,
                ),
            )
            if closed.rowcount and projected_failure is not None:
                receipt, encoded_attempts, encoded_staffing, encoded_hiring = projected_failure
                inserted = conn.execute(
                    "INSERT INTO preflight_failure_receipts "
                    "(id, session_id, trace_id, host, stage, reason_code, invariant_code, "
                    "exception_category, provider_attempts, staffing_reason_codes, "
                    "hiring_reason_codes, recorded_at) "
                    "SELECT ?, session_id, trace_id, host, ?, ?, ?, ?, ?, ?, ?, "
                    f"{STORE_CLOCK_SQL} FROM runs "  # nosec B608
                    "WHERE session_id = ? AND trace_id = ? AND status = 'preflight_failed'",
                    (
                        self._uuid(),
                        receipt["stage"],
                        receipt["reason_code"],
                        receipt["invariant_code"],
                        receipt["exception_category"],
                        encoded_attempts,
                        encoded_staffing,
                        encoded_hiring,
                        session_id,
                        trace_id,
                    ),
                )
                if inserted.rowcount != 1:
                    raise RuntimeError("preflight failure receipt lost turn correlation")
            conn.commit()
            return closed.rowcount == 1
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def mark_preflight_ready(
        self,
        *,
        session_id: str,
        trace_id: str,
        attempt_token: str,
        recipe: Mapping[str, Any],
        host: str,
        routing_evidence: Mapping[str, Any],
        suggestions: list[dict[str, Any]],
        specialist_refs: list[dict[str, Any]],
        codex_native_plan_scopes: list[dict[str, Any]] | None = None,
    ) -> dict[str, str]:
        """Atomically commit content-free child evidence with the ready CAS."""

        evidence = _prepare_ready_evidence(
            session_id=session_id,
            trace_id=trace_id,
            attempt_token=attempt_token,
            host=host,
            recipe=recipe,
            routing_evidence=routing_evidence,
            suggestions=suggestions,
            specialist_refs=specialist_refs,
        )
        normalized_session = evidence.session_id
        normalized_trace = evidence.trace_id
        normalized_attempt = evidence.attempt_token
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            now_value = str(
                conn.execute(
                    f"SELECT {STORE_CLOCK_SQL} AS now_value"  # nosec B608
                ).fetchone()["now_value"]
            )
            run = conn.execute(
                "SELECT status, host, preflight_state, preflight_attempt_token, "
                "preflight_lease_expires_at, preflight_result FROM runs "
                "WHERE session_id = ? AND trace_id = ?",
                (normalized_session, normalized_trace),
            ).fetchone()
            if (
                run is not None
                and (str(run["host"] or "unknown").strip().casefold()[:64] or "unknown")
                != evidence.host
            ):
                conn.commit()
                return {"outcome": "host_conflict"}
            if run is not None and (
                str(run["status"] or "") == "active"
                and str(run["preflight_state"] or "") == "ready"
                and str(run["preflight_attempt_token"] or "") == normalized_attempt
            ):
                replay = _decode_preflight_recipe(
                    run["preflight_result"],
                    session_id=normalized_session,
                    trace_id=normalized_trace,
                )
                if replay is not None:
                    _commit_codex_native_plan_scopes(
                        self,
                        conn,
                        evidence,
                        _project_codex_native_plan_scopes(
                            evidence,
                            [] if codex_native_plan_scopes is None else codex_native_plan_scopes,
                        ),
                    )
                    conn.execute(
                        f"UPDATE runs SET last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                        "WHERE session_id = ? AND trace_id = ?",
                        (normalized_session, normalized_trace),
                    )
                conn.commit()
                return {"outcome": "replay" if replay is not None else "cas_lost"}
            if run is None or (
                str(run["status"] or "") != "active"
                or str(run["preflight_state"] or "") != "in_progress"
                or str(run["preflight_attempt_token"] or "") != normalized_attempt
                or str(run["preflight_lease_expires_at"] or "") < now_value
            ):
                conn.commit()
                return {"outcome": "cas_lost"}
            if evidence.recipe.get("continuation_guard") is not None and not (
                _continuation_guard_matches(conn, evidence.recipe)
            ):
                conn.commit()
                return {"outcome": "continuation_guard_conflict"}
            projected_refs = evidence.specialist_refs
            projected_suggestions = evidence.suggestions
            projected_routing = evidence.routing
            encoded_recipe = evidence.encoded_recipe
            delivery_mode = evidence.delivery_mode
            resident_manager_binding = evidence.resident_manager_binding
            if resident_manager_binding is not None and not self._commit_resident_manager_binding(
                conn,
                session_id=normalized_session,
                trace_id=normalized_trace,
                binding=resident_manager_binding,
            ):
                conn.rollback()
                return {"outcome": "binding_conflict"}
            ready = conn.execute(
                "UPDATE runs SET preflight_state = 'ready', "
                "preflight_lease_expires_at = '', preflight_result = ?, "
                f"last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                "WHERE session_id = ? AND trace_id = ? AND status = 'active' "
                "AND preflight_state = 'in_progress' AND preflight_attempt_token = ? "
                "AND preflight_lease_expires_at >= ?",
                (
                    encoded_recipe,
                    normalized_session,
                    normalized_trace,
                    normalized_attempt,
                    now_value,
                ),
            )
            if ready.rowcount != 1:
                conn.rollback()
                return {"outcome": "cas_lost"}
            _commit_codex_native_plan_scopes(
                self,
                conn,
                evidence,
                _project_codex_native_plan_scopes(
                    evidence,
                    [] if codex_native_plan_scopes is None else codex_native_plan_scopes,
                ),
            )
            _commit_pending_hiring_evidence(self, conn, evidence)
            safe_decision = projected_routing["decision"]
            work_units = safe_decision.get("work_units") or {}
            conn.execute(
                "INSERT INTO routing_decisions "
                "(id, trace_id, session_id, query_hash, context_fingerprint, status, "
                "source, selected_ids, semantic_ids, companion_ids, confidence, "
                "latency_ms, provider, work_units, decision, created_at) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, {STORE_CLOCK_SQL})",  # nosec B608
                (
                    self._uuid(),
                    normalized_trace,
                    normalized_session,
                    projected_routing["query_hash"],
                    projected_routing["context_fingerprint"],
                    str(safe_decision.get("status") or "unknown"),
                    projected_routing["source"],
                    json.dumps(safe_decision.get("selected_ids") or []),
                    json.dumps(safe_decision.get("semantic_ids") or []),
                    json.dumps(safe_decision.get("available_companion_ids") or []),
                    _bounded_finite_float(safe_decision.get("confidence", 0.0)),
                    _bounded_nonnegative_int(
                        safe_decision.get("latency_ms", 0), maximum=86_400_000
                    ),
                    json.dumps(work_units, sort_keys=True),
                    json.dumps(safe_decision, sort_keys=True),
                ),
            )
            for receipt in evidence.model_receipts:
                conn.execute(
                    "INSERT INTO model_receipts "
                    "(id, trace_id, session_id, host, requested_model, model_group, "
                    "resolved_provider, resolved_model, api_base, attempted_fallbacks, "
                    "model_id, source, recorded_at, started_at, ended_at, status) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {STORE_CLOCK_SQL}, "  # nosec B608
                    "?, ?, ?)",
                    (
                        self._uuid(),
                        normalized_trace,
                        normalized_session,
                        receipt["host"],
                        receipt["requested_model"],
                        receipt["model_group"],
                        receipt["resolved_provider"],
                        receipt["resolved_model"],
                        receipt["api_base"],
                        receipt["attempted_fallbacks"],
                        receipt["model_id"],
                        receipt["source"],
                        receipt["started_at"] or now_value,
                        receipt["ended_at"] or now_value,
                        receipt["status"],
                    ),
                )
            for suggestion in projected_suggestions:
                conn.execute(
                    "INSERT INTO delegation_events "
                    "(id, trace_id, session_id, host, work_unit_id, recommended_agent, "
                    "status, backend, skip_reason, error, started_at, completed_at) "
                    f"VALUES (?, ?, ?, ?, ?, ?, 'suggested', '', '', '', {STORE_CLOCK_SQL}, NULL)",  # nosec B608
                    (
                        self._uuid(),
                        normalized_trace,
                        normalized_session,
                        evidence.host,
                        suggestion["work_unit_id"],
                        suggestion["recommended_agent"],
                    ),
                )
            if delivery_mode == "direct":
                for specialist in projected_refs:
                    conn.execute(
                        "INSERT INTO specialists_loaded "
                        "(id, session_id, trace_id, agent_slug, loaded_at, expired_at) "
                        f"VALUES (?, ?, ?, ?, {STORE_CLOCK_SQL}, NULL)",  # nosec B608
                        (
                            self._uuid(),
                            normalized_session,
                            normalized_trace,
                            specialist["slug"],
                        ),
                    )
            conn.commit()
            return {"outcome": "committed"}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
