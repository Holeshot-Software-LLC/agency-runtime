"""Immutable, fail-closed review evidence for quarantined roster candidates."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.roster.ingress import (
    MAX_AGENT_CONTENT_BYTES,
    MAX_PATH_TEXT_BYTES,
    MAX_SHORT_TEXT_BYTES,
    RosterSyncError,
    _hash_text,
    _json_list,
    _load_json,
    _require_bounded_text,
    _utf8_size,
    parse_agent_file,
)
from agency_runtime.core.roster.remediation import (
    CONTRACT_PROJECTION_RULE_ID,
    REMEDIATION_POLICY_REVISION,
    RemediationReceipt,
    RosterRemediationError,
    normalize_remediation_receipt,
    remediate_source_text,
)
from agency_runtime.core.roster.revisions import decode_revision_metadata
from agency_runtime.core.roster.semantic_projection import (
    SEMANTIC_PROJECTION_POLICY_HASH,
    contract_for_projected_candidate,
    verify_projected_candidate_contract,
    verify_projected_remediation,
)
from agency_runtime.core.store.schema import BOUNDED_REMEDIATION_EVENT_DETAIL_SQL
from agency_runtime.core.store.sqlite import Store

AUDIT_POLICY_VERSION = "roster-candidate-audit-v2"
MAX_AUDIT_FINDINGS = 128
MAX_INFERENCE_FINDINGS = 64
MAX_INFERENCE_ATTEMPTS = 6
MAX_RESULTS = 1_000
MAX_REMEDIATION_EVENT_BYTES = 256 * 1024
MAX_INFERENCE_EVIDENCE_BYTES = 32 * 1024
_BLOCKING = frozenset({"error", "critical"})
_SEVERITIES = frozenset({"info", "warning", "error", "critical"})
_STATUSES = frozenset({"pending", "approved", "activated", "rejected"})
_AUDIT_STATUSES = frozenset({"passed", "failed"})
_INFERENCE_STATUSES = frozenset({"not_requested", "passed", "failed", "unavailable"})
_VERDICTS = frozenset({"passed", "failed", "degraded"})
_AUDIT_ID_RE = re.compile(r"audit-[0-9a-f]{64}\Z")
_AUDIT_REVISION_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
_FINDING_ID_RE = re.compile(r"finding-[0-9a-f]{64}\Z")


class InferenceAuditAssistant(Protocol):
    """Optional semantic reviewer supplied by a configured provider boundary."""

    def __call__(self, candidate: Mapping[str, Any]) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class AuditFinding:
    source: Literal["deterministic", "conflict", "inference"]
    severity: Literal["info", "warning", "error", "critical"]
    code: str
    message: str
    evidence_hash: str

    def public_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "evidence_hash": self.evidence_hash,
        }


@dataclass(frozen=True, slots=True)
class CandidateRemediationEvidence:
    """Verified raw-to-projected candidate provenance used by audit and sync."""

    event_id: str
    event_order: int
    event_created_at: str
    candidate_id: str
    candidate_download_id: str
    candidate_hash: str
    source_download_id: str
    source_id: str
    source_slug: str
    source_hash: str
    source_content: str
    source_status: str
    origin: str
    relative_path: str
    receipt: RemediationReceipt


@dataclass(frozen=True, slots=True)
class _Rule:
    code: str
    severity: Literal["warning", "error", "critical"]
    message: str
    expression: re.Pattern[str]


def _rule(code: str, severity: str, message: str, expression: str) -> _Rule:
    return _Rule(  # type: ignore[arg-type]
        code,
        severity,
        message,
        re.compile(expression, re.IGNORECASE | re.DOTALL),
    )


_RULES = (
    _rule(
        "instruction_priority_escalation",
        "critical",
        "Prompt attempts to replace higher-priority or prior instructions.",
        r"\b(?:ignore|disregard|override)\s+(?:all\s+)?(?:previous|prior|system|developer)\s+instructions?\b",
    ),
    _rule(
        "download_execute_pipeline",
        "critical",
        "Prompt contains a download-and-execute pipeline.",
        r"\b(?:curl|wget)\b[^\r\n|]{0,512}\|\s*(?:ba)?sh\b|\b(?:iwr|invoke-webrequest)\b[^\r\n|]{0,512}\|\s*(?:iex|invoke-expression)\b",
    ),
    _rule(
        "destructive_root_command",
        "critical",
        "Prompt contains an unbounded destructive system command.",
        r"\brm\s+-rf\s+(?:/|~)(?=\s|$|[\"',}\]])|\bformat\s+[a-z]:|\bremove-item\s+(?:[a-z]:\\|/)\s+.*-recurse",
    ),
    _rule(
        "credential_exfiltration",
        "critical",
        "Prompt directs credentials or secrets to an external destination.",
        r"\b(?:send|upload|post|transmit|email)\b.{0,96}\b(?:credential|api[ _-]?key|access[ _-]?token|password|secret)\b",
    ),
    _rule(
        "encoded_execution",
        "critical",
        "Prompt combines encoded content with dynamic execution.",
        r"\b(?:eval|exec|invoke-expression)\b.{0,160}\b(?:base64|frombase64string|b64decode)\b|\b(?:base64|frombase64string|b64decode)\b.{0,160}\b(?:eval|exec|invoke-expression)\b",
    ),
    _rule(
        "unbounded_repository_read",
        "warning",
        "Prompt requests an unbounded repository, filesystem, or history read.",
        r"\b(?:read|scan|load|inspect)\s+(?:the\s+)?(?:entire|whole|all)\s+(?:filesystem|repository|repo|git history|home directory)\b",
    ),
    _rule(
        "external_mutation_assumption",
        "warning",
        "Prompt assumes an external mutation without an authorization boundary.",
        r"\b(?:always|automatically)\s+(?:open|create|close|merge|push|publish|deploy|send)\b",
    ),
    _rule(
        "suspicious_encoded_blob",
        "warning",
        "Prompt contains a long encoded-looking blob requiring human review.",
        r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{384,}={0,2}(?![A-Za-z0-9+/])",
    ),
)


def _canonical_hash(value: object) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return _hash_text(serialized)


AUDIT_POLICY_HASH = _canonical_hash(
    {
        "remediation_policy": REMEDIATION_POLICY_REVISION,
        "registered_projection_provenance": {
            "policy_hash": SEMANTIC_PROJECTION_POLICY_HASH,
            "required": True,
        },
        "rules": [(rule.code, rule.severity, rule.expression.pattern) for rule in _RULES],
        "version": AUDIT_POLICY_VERSION,
    }
)

_NEGATION_PREFIX = re.compile(
    r"(?:\bnever\b|\bdo\s+not\b|\bmust\s+not\b|\bshall\s+not\b|\bdon't\b|\bavoid\b)"
    r"[^.!?\r\n]{0,96}$",
    re.IGNORECASE,
)


def _token(value: object, label: str, limit: int = MAX_SHORT_TEXT_BYTES) -> str:
    text = _require_bounded_text(value, limit, label).strip()
    if not text:
        raise RosterSyncError(f"{label} must not be empty")
    return text


def _candidate_row(conn: Any, candidate_id: str) -> dict[str, Any]:
    candidate_id = _token(candidate_id, "candidate id")
    row = conn.execute(
        "SELECT c.*, d.source_id, d.content, d.hash AS download_hash, "
        "d.status AS download_status FROM agent_candidates AS c "
        "JOIN agent_downloads AS d ON d.id = c.download_id WHERE c.id = ?",
        (candidate_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"candidate not found: {candidate_id}")
    result = dict(row)
    content = str(result.get("content") or "")
    candidate_hash = str(result.get("hash") or "")
    if (
        str(result.get("status") or "") not in _STATUSES
        or _utf8_size(content) > MAX_AGENT_CONTENT_BYTES
        or candidate_hash != str(result.get("download_hash") or "")
        or candidate_hash != _hash_text(content)
    ):
        raise RosterSyncError(f"candidate {candidate_id} quarantine evidence is invalid")
    for field in ("categories", "capabilities", "tool_affinity"):
        result[field] = _json_list(result.get(field), label=f"candidate {field}")
    registered = contract_for_projected_candidate(
        str(result.get("slug") or ""),
        candidate_hash,
    )
    if registered is not None:
        result = {**registered, **result}
    return result


def candidate_record_from_connection(conn: Any, candidate_id: str) -> dict[str, Any]:
    """Return one fully normalized, integrity-checked quarantine candidate."""

    return _candidate_row(conn, candidate_id)


def _active_records(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT a.agent_slug, a.name, a.version, a.hash, v.metadata "
        "FROM agent_active AS a LEFT JOIN agent_versions AS v "
        "ON v.agent_slug = a.agent_slug AND v.version = a.version "
        "ORDER BY a.agent_slug LIMIT 1001"
    ).fetchall()
    if len(rows) > 1_000:
        raise RosterSyncError("active roster exceeds candidate-audit limit 1000")
    records = [dict(row) for row in rows]
    for record in records:
        record["metadata"] = decode_revision_metadata(record.get("metadata")) or {}
    return records


def _active_basis(records: Sequence[Mapping[str, Any]]) -> str:
    return _canonical_hash(
        [
            (record.get("agent_slug", ""), record.get("version", ""), record.get("hash", ""))
            for record in records
        ]
    )


def _finding(
    source: Literal["deterministic", "conflict", "inference"],
    severity: str,
    code: object,
    message: object,
    evidence: object,
) -> AuditFinding:
    normalized_severity = str(severity).strip().casefold()
    if normalized_severity not in _SEVERITIES:
        raise RosterSyncError("audit finding severity is invalid")
    return AuditFinding(
        source,
        normalized_severity,  # type: ignore[arg-type]
        _token(code, "audit finding code", 128),
        _token(message, "audit finding message", 2_048),
        _canonical_hash(evidence),
    )


def _routing_contract(content: str, candidate: Mapping[str, Any]) -> dict[str, Any]:
    registered = contract_for_projected_candidate(
        str(candidate.get("slug") or ""),
        str(candidate.get("hash") or ""),
    )
    if registered is not None:
        return {
            field: list(registered[field])
            for field in ("conflicts_with", "requires", "required_tools")
        } | {
            field: str(registered[field])
            for field in ("authority", "context_mode", "independence_group")
        }
    if not content.lstrip().startswith(("{", "---")):
        return {}
    try:
        parsed = parse_agent_file(content)
    except (RosterSyncError, TypeError, ValueError):
        return {}
    result: dict[str, Any] = {
        field: _json_list(parsed.get(field), label=f"candidate {field}")
        for field in ("conflicts_with", "requires", "required_tools")
    }
    result.update(
        {
            field: str(parsed.get(field) or "")
            for field in ("authority", "context_mode", "independence_group")
        }
    )
    if (
        result["authority"] not in {"advise", "plan", "modify", "review", "approve"}
        or result["context_mode"] not in {"direct_safe", "isolated_only"}
        or not result["independence_group"]
    ):
        return {}
    return result


def _actionable_match(rule: _Rule, content: str) -> re.Match[str] | None:
    """Ignore literal risk examples that are explicitly prohibited nearby."""

    match = rule.expression.search(content)
    while match is not None:
        prefix = content[max(0, match.start() - 128) : match.start()]
        if _NEGATION_PREFIX.search(prefix) is None:
            return match
        match = rule.expression.search(content, match.end())
    return None


def candidate_remediation_evidence_from_connection(
    conn: Any,
    candidate: Mapping[str, Any],
) -> CandidateRemediationEvidence | None:
    """Verify exact candidate remediation provenance without scanning lifetime history."""

    candidate_id = _token(candidate.get("id"), "candidate id")
    candidate_slug = _token(candidate.get("slug"), "candidate slug")
    oversized = conn.execute(
        "SELECT 1 FROM agent_import_events "
        "WHERE event_type = 'manifest_entry_remediated' AND agent_slug = ? "
        "AND length(CAST(detail AS BLOB)) > ? LIMIT 1",
        (candidate_slug, MAX_REMEDIATION_EVENT_BYTES),
    ).fetchone()
    if oversized is not None:
        raise RosterSyncError("candidate remediation event exceeds its audit bound")
    malformed = conn.execute(
        "SELECT 1 FROM agent_import_events "
        "WHERE event_type = 'manifest_entry_remediated' AND agent_slug = ? "
        "AND NOT json_valid(detail) LIMIT 1",
        (candidate_slug,),
    ).fetchone()
    malformed_identity = conn.execute(
        "SELECT 1 FROM agent_import_events "
        "WHERE event_type = 'manifest_entry_remediated' AND agent_slug = ? "
        "AND json_valid(detail) "
        "AND (json_type(detail, '$.candidate_id') IS NULL "
        "OR json_type(detail, '$.candidate_id') != 'text') LIMIT 1",
        (candidate_slug,),
    ).fetchone()
    if malformed is not None or malformed_identity is not None:
        raise RosterSyncError("candidate remediation event identity is invalid")
    rows = conn.execute(
        "SELECT event_sequence AS event_order, id, agent_slug, detail, created_at "
        "FROM agent_import_events "
        "WHERE event_type = 'manifest_entry_remediated' AND agent_slug = ? "
        f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, "
        "'$.candidate_id') = ? "
        "ORDER BY created_at DESC, event_sequence DESC LIMIT 2",  # nosec B608
        (candidate_slug, candidate_id),
    ).fetchall()
    if not rows:
        return None
    if len(rows) != 1:
        raise RosterSyncError("candidate has ambiguous remediation evidence")
    event_row = rows[0]
    event_order = event_row["event_order"]
    if isinstance(event_order, bool) or not isinstance(event_order, int) or event_order < 1:
        raise RosterSyncError("candidate remediation event order is invalid")
    detail_text = str(event_row["detail"] or "")
    if len(detail_text.encode("utf-8")) > MAX_REMEDIATION_EVENT_BYTES:
        raise RosterSyncError("candidate remediation event exceeds its audit bound")
    detail = _load_json(detail_text, "candidate remediation event")
    if (
        not isinstance(detail, Mapping)
        or detail.get("candidate_id") != candidate_id
        or set(detail)
        != {
            "candidate_download_id",
            "candidate_id",
            "origin",
            "receipt",
            "relative_path",
            "source_download_id",
            "source_id",
        }
    ):
        raise RosterSyncError("candidate remediation event fields are invalid")
    try:
        receipt = normalize_remediation_receipt(detail.get("receipt"))
    except RosterRemediationError as exc:
        raise RosterSyncError("candidate remediation receipt is invalid") from exc
    event_id = _token(event_row["id"], "candidate remediation event id")
    event_created_at = _token(
        event_row["created_at"],
        "candidate remediation event timestamp",
    )
    candidate_download_id = _token(
        detail.get("candidate_download_id"),
        "candidate remediation download id",
    )
    source_download_id = _token(
        detail.get("source_download_id"),
        "candidate remediation source download id",
    )
    source_id = _token(detail.get("source_id"), "candidate remediation source id")
    origin = _token(
        detail.get("origin"),
        "candidate remediation origin",
        MAX_PATH_TEXT_BYTES,
    )
    relative_path = _token(
        detail.get("relative_path"),
        "candidate remediation relative path",
        MAX_PATH_TEXT_BYTES,
    )
    if str(
        event_row["agent_slug"] or ""
    ) != candidate_slug or candidate_download_id != candidate.get("download_id"):
        raise RosterSyncError("candidate remediation download binding is invalid")
    source_row = conn.execute(
        "SELECT d.source_id, d.slug, d.hash, d.content, d.status, "
        "c.id AS candidate_id FROM agent_downloads d "
        "LEFT JOIN agent_candidates c ON c.download_id = d.id WHERE d.id = ?",
        (source_download_id,),
    ).fetchone()
    if source_row is None:
        raise RosterSyncError("candidate remediation source bytes are unavailable")
    original = str(source_row["content"] or "")
    if _utf8_size(original) > MAX_AGENT_CONTENT_BYTES:
        raise RosterSyncError("candidate remediation source bytes exceed their audit bound")
    repaired, known = remediate_source_text(original)
    known_rule = known.rules[0].public_dict() if known is not None else {}
    receipt_rule = receipt.rules[0].public_dict()
    for finding_field in ("findings_resolved", "findings_unresolved"):
        known_rule.pop(finding_field, None)
        receipt_rule.pop(finding_field, None)
    if (
        known is None
        or source_id != candidate.get("source_id")
        or origin != candidate.get("prompt_path")
        or source_row["source_id"] != candidate.get("source_id")
        or source_row["slug"] != candidate.get("slug")
        or source_row["hash"] != receipt.original_hash
        or source_row["status"] != "quarantined"
        or source_row["candidate_id"] is not None
        or known_rule != receipt_rule
        or _hash_text(repaired) != receipt.rules[0].after_hash
        or _hash_text(str(candidate.get("content") or "")) != receipt.transformed_hash
        or candidate.get("hash") != receipt.transformed_hash
    ):
        raise RosterSyncError("candidate remediation evidence does not bind its artifacts")
    try:
        verify_projected_remediation(
            original,
            str(candidate.get("content") or ""),
            receipt,
            relative_path=relative_path,
        )
        verify_projected_candidate_contract(
            candidate,
            source_hash=receipt.original_hash,
            relative_path=relative_path,
        )
    except RosterRemediationError as exc:
        raise RosterSyncError("candidate remediation semantic projection is invalid") from exc
    return CandidateRemediationEvidence(
        event_id=event_id,
        event_order=event_order,
        event_created_at=event_created_at,
        candidate_id=candidate_id,
        candidate_download_id=candidate_download_id,
        candidate_hash=str(candidate.get("hash") or ""),
        source_download_id=source_download_id,
        source_id=source_id,
        source_slug=str(source_row["slug"] or ""),
        source_hash=str(source_row["hash"] or ""),
        source_content=original,
        source_status=str(source_row["status"] or ""),
        origin=origin,
        relative_path=relative_path,
        receipt=receipt,
    )


def _candidate_remediation_receipt(
    conn: Any,
    candidate: Mapping[str, Any],
) -> RemediationReceipt | None:
    evidence = candidate_remediation_evidence_from_connection(conn, candidate)
    return None if evidence is None else evidence.receipt


def _deterministic_review(
    conn: Any,
    candidate: Mapping[str, Any],
) -> tuple[list[AuditFinding], str, dict[str, Any]]:
    content = str(candidate.get("content") or "")
    remediation = _candidate_remediation_receipt(conn, candidate)
    registered_projection = contract_for_projected_candidate(
        str(candidate.get("slug") or ""),
        str(candidate.get("hash") or ""),
    )
    findings = [
        _finding(
            "deterministic",
            rule.severity,
            rule.code,
            rule.message,
            {"end": match.end(), "rule": rule.code, "start": match.start()},
        )
        for rule in _RULES
        if (match := _actionable_match(rule, content)) is not None
    ]
    if registered_projection is not None and remediation is None:
        findings.append(
            _finding(
                "deterministic",
                "error",
                "registered_projection_provenance_required",
                "A registered projected candidate requires its source-bound remediation receipt.",
                {
                    "candidate_id": candidate.get("id", ""),
                    "source_content_hash": registered_projection["source_content_hash"],
                },
            )
        )
    if remediation is not None and (
        remediation.rules[-1].rule_id != CONTRACT_PROJECTION_RULE_ID
        or remediation.rules[-1].kind != "semantic_projection"
        or remediation.findings_unresolved
    ):
        findings.append(
            _finding(
                "deterministic",
                "error",
                "semantic_projection_required",
                "Encoding repair is non-executable until a reviewed semantic projection "
                "binds the final candidate hash and resolves every finding.",
                {
                    "candidate_id": candidate.get("id", ""),
                    "receipt_hash": _canonical_hash(remediation.public_dict()),
                },
            )
        )
    contract = _routing_contract(content, candidate)
    active = _active_records(conn)
    slug = str(candidate.get("slug") or "")
    name = str(candidate.get("name") or "").strip().casefold()
    findings.extend(
        _finding(
            "conflict",
            "error",
            "duplicate_display_identity",
            "Another active agent has the same normalized display identity.",
            {"active_slug": record["agent_slug"], "candidate_slug": slug},
        )
        for record in active
        if (
            str(record.get("agent_slug") or "") != slug
            and name
            and str(record.get("name") or "").strip().casefold() == name
        )
    )
    available = {str(record.get("agent_slug") or "") for record in active}
    available.update(
        str(row["slug"])
        for row in conn.execute(
            "SELECT slug FROM agent_candidates WHERE status IN ('pending', 'approved', 'activated')"
        ).fetchall()
    )
    findings.extend(
        _finding(
            "conflict",
            "error",
            "missing_required_agent",
            "A declared required agent is absent from active and reviewable candidates.",
            {"candidate_slug": slug, "required_slug": required},
        )
        for required in contract.get("requires", [])
        if required not in available
    )
    findings.extend(
        _finding(
            "conflict",
            "info",
            "declared_active_conflict",
            "A declared conflict must remain isolated during routing.",
            {"candidate_slug": slug, "conflict_slug": conflict},
        )
        for conflict in contract.get("conflicts_with", [])
        if conflict in available
    )
    if not contract:
        findings.append(
            _finding(
                "deterministic",
                "error",
                "routing_contract_requires_review",
                "The source does not carry a complete governed routing contract.",
                {"candidate_slug": slug},
            )
        )
    if not str(candidate.get("source") or "") or not str(candidate.get("source_version") or ""):
        findings.append(
            _finding(
                "deterministic",
                "warning",
                "provenance_requires_review",
                "Source provenance or source revision is incomplete.",
                {"candidate_slug": slug},
            )
        )
    if len(findings) > MAX_AUDIT_FINDINGS:
        raise RosterSyncError("candidate audit produced too many findings")
    payload = {
        "candidate_hash": candidate.get("hash", ""),
        "description": candidate.get("description", ""),
        "name": candidate.get("name", ""),
        "prompt_body": content,
        "routing_contract": contract,
        "slug": slug,
        "source": candidate.get("source", ""),
        "source_version": candidate.get("source_version", ""),
        "version": candidate.get("version", ""),
    }
    return findings, _active_basis(active), payload


def _evidence_text(value: object, label: str, maximum: int) -> str:
    text = _require_bounded_text(value or "", maximum, label).strip()
    if "\x00" in text:
        raise RosterSyncError(f"{label} contains a null character")
    return text


def _validated_inference_evidence(
    value: object,
    *,
    provider: str,
) -> dict[str, Any]:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise RosterSyncError("inference audit evidence must be a mapping")
    attempts = value.get("attempts", [])
    if not isinstance(attempts, list) or len(attempts) > MAX_INFERENCE_ATTEMPTS:
        raise RosterSyncError("inference audit attempts are invalid or unbounded")

    def identity(raw: Mapping[str, Any]) -> dict[str, str]:
        provider_type = _evidence_text(
            raw.get("provider_type"), "inference provider type", 32
        ).casefold()
        requested_model = _evidence_text(
            raw.get("requested_model"), "inference requested model", 512
        )
        return {
            "provider_name": _evidence_text(
                raw.get("provider_name"), "inference provider name", 128
            ),
            "provider_type": provider_type,
            "requested_model": requested_model,
            "model_group": _evidence_text(raw.get("model_group"), "inference model group", 512)
            if provider_type == "litellm"
            else "",
            # The roster-audit provider boundary has no authoritative reconciled
            # model receipt. Ignore caller claims rather than promoting aliases.
            "actual_model": "",
        }

    normalized_attempts: list[dict[str, str]] = []
    for raw in attempts:
        if not isinstance(raw, Mapping):
            raise RosterSyncError("inference audit attempts must be mappings")
        normalized_attempts.append(
            {
                **identity(raw),
                "status": _evidence_text(raw.get("status"), "inference attempt status", 32),
                "reason": _evidence_text(raw.get("reason"), "inference attempt reason", 128),
            }
        )
    normalized = identity(value)
    if not normalized["provider_name"]:
        normalized["provider_name"] = provider
    normalized["attempts"] = normalized_attempts
    return normalized


def _validated_inference(
    value: Mapping[str, Any],
) -> tuple[str, str, list[AuditFinding], dict[str, Any]]:
    if not isinstance(value, Mapping):
        raise RosterSyncError("inference audit result must be a mapping")
    status = str(value.get("status") or "").strip().casefold()
    if status not in {"passed", "failed", "unavailable"}:
        raise RosterSyncError("inference audit status must be passed, failed, or unavailable")
    provider = _require_bounded_text(
        value.get("provider") or "inference-assistant",
        256,
        "inference audit provider",
    ).strip()
    raw_findings = value.get("findings", [])
    if not isinstance(raw_findings, list) or len(raw_findings) > MAX_INFERENCE_FINDINGS:
        raise RosterSyncError("inference audit findings are invalid or unbounded")
    findings: list[AuditFinding] = []
    for index, raw in enumerate(raw_findings):
        if not isinstance(raw, Mapping):
            raise RosterSyncError("inference audit findings must be mappings")
        code = str(raw.get("code") or "").strip().casefold()
        if not re.fullmatch(r"[a-z][a-z0-9_.:-]{0,127}", code):
            code = f"inference_finding_{index + 1}"
        raw_message = str(raw.get("message") or "Inference review finding.")
        findings.append(
            _finding(
                "inference",
                str(raw.get("severity") or "warning"),
                code,
                f"Inference review classified this candidate as {code}.",
                {
                    "code": code,
                    "index": index,
                    "message_hash": _hash_text(raw_message),
                },
            )
        )
    if status == "passed" and any(item.severity in _BLOCKING for item in findings):
        status = "failed"
    if status == "failed" and not any(item.severity in _BLOCKING for item in findings):
        findings.append(
            _finding(
                "inference",
                "error",
                "inference_rejected_candidate",
                "Inference review rejected the candidate without a blocking finding.",
                {"provider": provider},
            )
        )
    if status == "unavailable" and not findings:
        findings.append(
            _finding(
                "inference",
                "warning",
                "inference_audit_unavailable",
                "Configured inference did not return valid audit evidence.",
                {"provider": provider},
            )
        )
    evidence = _validated_inference_evidence(
        value.get("inference_evidence"),
        provider=provider,
    )
    return status, provider, findings, evidence


def _audit_status(
    findings: Sequence[AuditFinding],
    inference_status: str,
) -> tuple[str, str]:
    deterministic = (
        "failed"
        if any(item.source != "inference" and item.severity in _BLOCKING for item in findings)
        else "passed"
    )
    if inference_status == "unavailable":
        return deterministic, "degraded"
    if (
        deterministic == "failed"
        or inference_status == "failed"
        or any(item.source == "inference" and item.severity in _BLOCKING for item in findings)
    ):
        return deterministic, "failed"
    return deterministic, "passed"


def record_candidate_status_event(
    conn: Any,
    store: Store,
    candidate_id: str,
    *,
    event_type: str,
    from_status: str,
    to_status: str,
    reason: str = "",
    audit_id: str = "",
    created_at: str | None = None,
) -> str:
    """Append one bounded status event inside the caller's transaction."""

    candidate_id = _token(candidate_id, "candidate id")
    event_type = _token(event_type, "candidate event type")
    from_status = _require_bounded_text(from_status, MAX_SHORT_TEXT_BYTES, "prior status")
    to_status = _token(to_status, "candidate status")
    reason = _require_bounded_text(reason, 2_048, "candidate status reason")
    audit_id = _require_bounded_text(audit_id, MAX_SHORT_TEXT_BYTES, "candidate audit id")
    event_id = store._uuid()
    conn.execute(
        "INSERT INTO agent_candidate_status_events "
        "(id, candidate_id, event_type, from_status, to_status, reason, audit_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event_id,
            candidate_id,
            event_type,
            from_status,
            to_status,
            reason,
            audit_id,
            created_at or store._now(),
        ),
    )
    return event_id


def _stored_text(
    value: object,
    *,
    label: str,
    maximum: int,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise RosterSyncError(f"stored {label} must be text")
    try:
        text = _require_bounded_text(value, maximum, f"stored {label}")
    except (TypeError, UnicodeError) as exc:
        raise RosterSyncError(f"stored {label} is invalid") from exc
    if not allow_empty and not text:
        raise RosterSyncError(f"stored {label} must not be empty")
    return text


def _stored_timestamp(value: object, *, label: str) -> tuple[str, datetime]:
    text = _stored_text(value, label=label, maximum=MAX_SHORT_TEXT_BYTES)
    try:
        timestamp = datetime.fromisoformat(text)
    except ValueError as exc:
        raise RosterSyncError(f"stored {label} is invalid") from exc
    if timestamp.tzinfo is None:
        raise RosterSyncError(f"stored {label} is invalid")
    return text, timestamp


def _audit_from_connection(conn: Any, audit_id: object) -> dict[str, Any]:
    audit_id = _stored_text(audit_id, label="candidate audit id", maximum=MAX_SHORT_TEXT_BYTES)
    if not _AUDIT_ID_RE.fullmatch(audit_id):
        raise RosterSyncError("stored candidate audit id is invalid")
    row = conn.execute("SELECT * FROM agent_candidate_audits WHERE id = ?", (audit_id,)).fetchone()
    if row is None:
        raise KeyError(f"candidate audit not found: {audit_id}")

    result = dict(row)
    exact_id = _stored_text(
        result.get("id"),
        label="candidate audit id",
        maximum=MAX_SHORT_TEXT_BYTES,
    )
    candidate_id = _stored_text(
        result.get("candidate_id"),
        label="candidate audit candidate id",
        maximum=MAX_SHORT_TEXT_BYTES,
    )
    audit_revision = _stored_text(
        result.get("audit_revision"),
        label="candidate audit revision",
        maximum=MAX_SHORT_TEXT_BYTES,
    )
    policy_hash = _stored_text(
        result.get("policy_hash"),
        label="candidate audit policy hash",
        maximum=64,
    )
    candidate_version = _stored_text(
        result.get("candidate_version"),
        label="candidate audit version",
        maximum=MAX_SHORT_TEXT_BYTES,
    )
    candidate_hash = _stored_text(
        result.get("candidate_hash"),
        label="candidate audit candidate hash",
        maximum=64,
    )
    active_basis_hash = _stored_text(
        result.get("active_basis_hash"),
        label="candidate audit active basis hash",
        maximum=64,
    )
    deterministic_status = _stored_text(
        result.get("deterministic_status"),
        label="candidate audit deterministic status",
        maximum=32,
    )
    inference_status = _stored_text(
        result.get("inference_status"),
        label="candidate audit inference status",
        maximum=32,
    )
    verdict = _stored_text(
        result.get("verdict"),
        label="candidate audit verdict",
        maximum=32,
    )
    provider = _stored_text(
        result.get("provider"),
        label="candidate audit provider",
        maximum=256,
        allow_empty=True,
    )
    created_at, audit_created_at = _stored_timestamp(
        result.get("created_at"),
        label="candidate audit timestamp",
    )
    if (
        exact_id != audit_id
        or not _AUDIT_REVISION_RE.fullmatch(audit_revision)
        or not _DIGEST_RE.fullmatch(policy_hash)
        or not _DIGEST_RE.fullmatch(candidate_hash)
        or not _DIGEST_RE.fullmatch(active_basis_hash)
        or deterministic_status not in _AUDIT_STATUSES
        or inference_status not in _INFERENCE_STATUSES
        or verdict not in _VERDICTS
    ):
        raise RosterSyncError("stored candidate audit identity is invalid")

    raw_evidence = result.get("inference_evidence")
    if not isinstance(raw_evidence, (str, bytes)):
        raise RosterSyncError("stored inference audit evidence must be text")
    try:
        decoded_evidence = safe_load_bounded_json(
            raw_evidence,
            maximum_bytes=MAX_INFERENCE_EVIDENCE_BYTES,
            maximum_depth=6,
            maximum_nodes=128,
        )
    except (BoundedJSONError, TypeError, ValueError) as exc:
        raise RosterSyncError("stored inference audit evidence is invalid") from exc
    if not isinstance(raw_evidence, str):
        raise RosterSyncError("stored inference audit evidence must be text")
    evidence = _validated_inference_evidence(decoded_evidence, provider=provider)
    canonical_evidence = json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if raw_evidence != canonical_evidence:
        raise RosterSyncError("stored inference audit evidence is not canonical")

    raw_findings = conn.execute(
        "SELECT id, source, severity, code, message, evidence_hash, created_at "
        "FROM agent_candidate_audit_findings WHERE audit_id = ? "
        "LIMIT ?",
        (audit_id, MAX_AUDIT_FINDINGS + 1),
    ).fetchall()
    if len(raw_findings) > MAX_AUDIT_FINDINGS:
        raise RosterSyncError("stored candidate audit findings exceed the limit")
    findings: list[dict[str, str]] = []
    for raw in raw_findings:
        finding = dict(raw)
        finding_id = _stored_text(
            finding.get("id"),
            label="candidate audit finding id",
            maximum=MAX_SHORT_TEXT_BYTES,
        )
        source = _stored_text(
            finding.get("source"),
            label="candidate audit finding source",
            maximum=32,
        )
        severity = _stored_text(
            finding.get("severity"),
            label="candidate audit finding severity",
            maximum=32,
        )
        code = _stored_text(
            finding.get("code"),
            label="candidate audit finding code",
            maximum=128,
        )
        message = _stored_text(
            finding.get("message"),
            label="candidate audit finding message",
            maximum=2_048,
        )
        evidence_hash = _stored_text(
            finding.get("evidence_hash"),
            label="candidate audit finding evidence hash",
            maximum=64,
        )
        finding_created_at, parsed_finding_timestamp = _stored_timestamp(
            finding.get("created_at"),
            label="candidate audit finding timestamp",
        )
        public_finding = {
            "source": source,
            "severity": severity,
            "code": code,
            "message": message,
            "evidence_hash": evidence_hash,
        }
        expected_finding_id = "finding-" + _canonical_hash({"audit_id": audit_id, **public_finding})
        if (
            not _FINDING_ID_RE.fullmatch(finding_id)
            or finding_id != expected_finding_id
            or source not in {"deterministic", "conflict", "inference"}
            or severity not in _SEVERITIES
            or not _DIGEST_RE.fullmatch(evidence_hash)
            or finding_created_at != created_at
            or parsed_finding_timestamp != audit_created_at
        ):
            raise RosterSyncError("stored candidate audit finding is invalid")
        findings.append({**public_finding, "created_at": finding_created_at})
    findings.sort(
        key=lambda item: (
            item["source"],
            item["severity"],
            item["code"],
            item["evidence_hash"],
        )
    )

    finding_identity = [
        {
            field: finding[field]
            for field in ("source", "severity", "code", "message", "evidence_hash")
        }
        for finding in findings
    ]
    identity = {
        "active_basis_hash": active_basis_hash,
        "candidate_hash": candidate_hash,
        "candidate_id": candidate_id,
        "candidate_version": candidate_version,
        "deterministic_status": deterministic_status,
        "findings": finding_identity,
        "inference_status": inference_status,
        "policy_hash": policy_hash,
        "provider": provider,
        "inference_evidence": evidence,
        "verdict": verdict,
    }
    expected_revision = "sha256:" + _canonical_hash(identity)
    expected_audit_id = "audit-" + _canonical_hash(
        {"candidate_id": candidate_id, "revision": expected_revision}
    )
    if audit_revision != expected_revision or audit_id != expected_audit_id:
        raise RosterSyncError("stored candidate audit integrity check failed")

    return {
        "id": exact_id,
        "candidate_id": candidate_id,
        "audit_revision": audit_revision,
        "policy_hash": policy_hash,
        "candidate_version": candidate_version,
        "candidate_hash": candidate_hash,
        "active_basis_hash": active_basis_hash,
        "deterministic_status": deterministic_status,
        "inference_status": inference_status,
        "verdict": verdict,
        "provider": provider,
        "inference_evidence": evidence,
        "created_at": created_at,
        "findings": findings,
    }


def _persist_audit(
    conn: Any,
    store: Store,
    candidate: Mapping[str, Any],
    *,
    active_basis_hash: str,
    findings: Sequence[AuditFinding],
    inference_status: str,
    provider: str,
    inference_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if inference_status not in {"not_requested", "passed", "failed", "unavailable"}:
        raise RosterSyncError("candidate inference status is invalid")
    provider = _evidence_text(provider, "inference audit provider", 256)
    evidence = _validated_inference_evidence(inference_evidence, provider=provider)
    evidence_json = json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    deterministic, verdict = _audit_status(findings, inference_status)
    finding_rows = sorted(
        (item.public_dict() for item in findings),
        key=lambda item: (item["source"], item["severity"], item["code"], item["evidence_hash"]),
    )
    identity = {
        "active_basis_hash": active_basis_hash,
        "candidate_hash": candidate.get("hash", ""),
        "candidate_id": candidate.get("id", ""),
        "candidate_version": candidate.get("version", ""),
        "deterministic_status": deterministic,
        "findings": finding_rows,
        "inference_status": inference_status,
        "policy_hash": AUDIT_POLICY_HASH,
        "provider": provider,
        "inference_evidence": evidence,
        "verdict": verdict,
    }
    audit_revision = "sha256:" + _canonical_hash(identity)
    existing = conn.execute(
        "SELECT id FROM agent_candidate_audits WHERE candidate_id = ? AND audit_revision = ?",
        (candidate["id"], audit_revision),
    ).fetchone()
    if existing is not None:
        return _audit_from_connection(conn, existing["id"])
    audit_id = "audit-" + _canonical_hash(
        {"candidate_id": candidate["id"], "revision": audit_revision}
    )
    now = store._now()
    conn.execute(
        "INSERT INTO agent_candidate_audits "
        "(id, candidate_id, audit_revision, policy_hash, candidate_version, candidate_hash, "
        "active_basis_hash, deterministic_status, inference_status, verdict, provider, "
        "inference_evidence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            audit_id,
            candidate["id"],
            audit_revision,
            AUDIT_POLICY_HASH,
            candidate.get("version", ""),
            candidate.get("hash", ""),
            active_basis_hash,
            deterministic,
            inference_status,
            verdict,
            provider,
            evidence_json,
            now,
        ),
    )
    for finding in finding_rows:
        finding_id = "finding-" + _canonical_hash({"audit_id": audit_id, **finding})
        conn.execute(
            "INSERT INTO agent_candidate_audit_findings "
            "(id, audit_id, source, severity, code, message, evidence_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                finding_id,
                audit_id,
                finding["source"],
                finding["severity"],
                finding["code"],
                finding["message"],
                finding["evidence_hash"],
                now,
            ),
        )
    record_candidate_status_event(
        conn,
        store,
        str(candidate["id"]),
        event_type="audited",
        from_status=str(candidate["status"]),
        to_status=str(candidate["status"]),
        reason=f"audit_verdict={verdict}",
        audit_id=audit_id,
        created_at=now,
    )
    return _audit_from_connection(conn, audit_id)


def audit_candidate_in_connection(
    conn: Any,
    store: Store,
    candidate_id: str,
    *,
    require_inference: bool = False,
) -> dict[str, Any]:
    """Run deterministic audit and optionally install a fail-closed placeholder."""

    candidate = _candidate_row(conn, candidate_id)
    findings, active_basis_hash, _payload = _deterministic_review(conn, candidate)
    inference_status = "unavailable" if require_inference else "not_requested"
    if require_inference:
        findings.append(
            _finding(
                "inference",
                "warning",
                "inference_audit_pending",
                "Configured inference audit has not completed.",
                {"candidate_id": candidate_id},
            )
        )
    return _persist_audit(
        conn,
        store,
        candidate,
        active_basis_hash=active_basis_hash,
        findings=findings,
        inference_status=inference_status,
        provider="",
        inference_evidence={"attempts": []},
    )


def run_candidate_audit(
    store: Store,
    candidate_id: str,
    *,
    inference_assistant: InferenceAuditAssistant | None = None,
    require_inference: bool = False,
) -> dict[str, Any]:
    """Audit without holding a database write lock across optional inference."""

    conn = store._connect()
    try:
        conn.execute("BEGIN")
        candidate = _candidate_row(conn, candidate_id)
        findings, active_basis_hash, payload = _deterministic_review(conn, candidate)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    inference_status = "not_requested"
    provider = ""
    inference_evidence: dict[str, Any] = {"attempts": []}
    if inference_assistant is not None:
        try:
            inference_status, provider, inferred, inference_evidence = _validated_inference(
                inference_assistant(payload)
            )
            findings.extend(inferred)
        except Exception as exc:
            inference_status = "unavailable"
            provider = type(exc).__name__
            findings.append(
                _finding(
                    "inference",
                    "warning",
                    "inference_audit_unavailable",
                    "Inference audit was unavailable or returned invalid evidence.",
                    {"exception_type": type(exc).__name__},
                )
            )
    elif require_inference:
        inference_status = "unavailable"
        findings.append(
            _finding(
                "inference",
                "warning",
                "inference_audit_unavailable",
                "Inference audit was required but no assistant was available.",
                {"candidate_id": candidate_id},
            )
        )

    conn = store._connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        current = _candidate_row(conn, candidate_id)
        if (
            current.get("version") != candidate.get("version")
            or current.get("hash") != candidate.get("hash")
            or _active_basis(_active_records(conn)) != active_basis_hash
        ):
            raise RosterSyncError("candidate audit basis changed; retry the audit")
        result = _persist_audit(
            conn,
            store,
            current,
            active_basis_hash=active_basis_hash,
            findings=findings,
            inference_status=inference_status,
            provider=provider,
            inference_evidence=inference_evidence,
        )
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def latest_candidate_audit_from_connection(
    conn: Any,
    candidate_id: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id FROM agent_candidate_audits WHERE candidate_id = ? "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1",
        (candidate_id,),
    ).fetchone()
    return None if row is None else _audit_from_connection(conn, row["id"])


def refresh_candidate_audit_basis_in_connection(
    conn: Any,
    store: Store,
    candidate_id: str,
) -> dict[str, Any] | None:
    """Refresh active-roster checks without repeating the content-bound inference call."""

    candidate = _candidate_row(conn, candidate_id)
    prior = latest_candidate_audit_from_connection(conn, candidate_id)
    if prior is None:
        return None
    if (
        prior["policy_hash"] != AUDIT_POLICY_HASH
        or prior["candidate_version"] != candidate.get("version")
        or prior["candidate_hash"] != candidate.get("hash")
    ):
        return prior
    deterministic_findings, active_basis_hash, _payload = _deterministic_review(conn, candidate)
    if prior["active_basis_hash"] == active_basis_hash:
        return prior

    inference_findings: list[AuditFinding] = []
    for raw in prior["findings"]:
        if str(raw.get("source") or "") != "inference":
            continue
        severity = str(raw.get("severity") or "").strip().casefold()
        evidence_hash = _evidence_text(
            raw.get("evidence_hash"),
            "inference finding evidence hash",
            64,
        )
        if severity not in _SEVERITIES or not re.fullmatch(r"[0-9a-f]{64}", evidence_hash):
            raise RosterSyncError("stored inference finding evidence is invalid")
        inference_findings.append(
            AuditFinding(
                "inference",
                severity,  # type: ignore[arg-type]
                _token(raw.get("code"), "inference finding code", 128),
                _token(raw.get("message"), "inference finding message", 2_048),
                evidence_hash,
            )
        )
    return _persist_audit(
        conn,
        store,
        candidate,
        active_basis_hash=active_basis_hash,
        findings=[*deterministic_findings, *inference_findings],
        inference_status=str(prior["inference_status"]),
        provider=str(prior["provider"]),
        inference_evidence=prior["inference_evidence"],
    )


def list_candidate_audits(
    store: Store,
    candidate_id: str,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return bounded immutable audit history for one candidate."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS:
        raise ValueError(f"audit result limit must be between 1 and {MAX_RESULTS}")
    candidate_id = _token(candidate_id, "candidate id")
    conn = store._connect()
    try:
        _candidate_row(conn, candidate_id)
        rows = conn.execute(
            "SELECT id FROM agent_candidate_audits WHERE candidate_id = ? "
            "ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (candidate_id, limit),
        ).fetchall()
        return [_audit_from_connection(conn, row["id"]) for row in rows]
    finally:
        conn.close()


def assert_bound_candidate_audit_from_connection(
    conn: Any,
    *,
    audit_id: str,
    candidate_id: str,
    candidate_version: str,
    candidate_hash: str,
    require_current_policy: bool,
) -> tuple[dict[str, Any], bool]:
    """Validate one immutable passing audit without rebasing its active-roster evidence."""

    if not isinstance(require_current_policy, bool):
        raise RosterSyncError("candidate audit current-policy requirement must be boolean")
    audit_id = _stored_text(
        audit_id,
        label="bound candidate audit id",
        maximum=MAX_SHORT_TEXT_BYTES,
    )
    candidate_id = _stored_text(
        candidate_id,
        label="bound candidate id",
        maximum=MAX_SHORT_TEXT_BYTES,
    )
    candidate_version = _stored_text(
        candidate_version,
        label="bound candidate version",
        maximum=MAX_SHORT_TEXT_BYTES,
    )
    candidate_hash = _stored_text(
        candidate_hash,
        label="bound candidate hash",
        maximum=64,
    )
    if not _AUDIT_ID_RE.fullmatch(audit_id) or not _DIGEST_RE.fullmatch(candidate_hash):
        raise RosterSyncError("candidate audit binding is invalid")
    audit = _audit_from_connection(conn, audit_id)
    policy_current = audit["policy_hash"] == AUDIT_POLICY_HASH
    if (
        audit["candidate_id"] != candidate_id
        or audit["candidate_version"] != candidate_version
        or audit["candidate_hash"] != candidate_hash
        or audit["deterministic_status"] != "passed"
        or audit["verdict"] != "passed"
        or (require_current_policy and not policy_current)
    ):
        raise RosterSyncError(f"candidate {candidate_id} does not have a bound passing audit")
    return audit, policy_current


def assert_candidate_audits_current(
    conn: Any,
    candidates: Sequence[Mapping[str, Any]],
    *,
    require_inference: bool = False,
) -> dict[str, str]:
    """Require current passing audits and return their immutable identifiers."""

    active_basis_hash = _active_basis(_active_records(conn))
    audit_ids: dict[str, str] = {}
    for candidate in candidates:
        candidate_id = str(candidate.get("id") or "")
        audit = latest_candidate_audit_from_connection(conn, candidate_id)
        if audit is None:
            raise RosterSyncError(f"candidate {candidate_id} has no audit evidence")
        if (
            audit["policy_hash"] != AUDIT_POLICY_HASH
            or audit["candidate_version"] != candidate.get("version")
            or audit["candidate_hash"] != candidate.get("hash")
            or audit["active_basis_hash"] != active_basis_hash
            or audit["verdict"] != "passed"
            or (require_inference and audit["inference_status"] != "passed")
        ):
            raise RosterSyncError(f"candidate {candidate_id} does not have a current passing audit")
        audit_ids[candidate_id] = str(audit["id"])
    return audit_ids


def reject_candidate(store: Store, candidate_id: str, *, reason: str) -> dict[str, Any]:
    """Reject a candidate while preserving any prior active revision."""

    reason = _token(reason, "candidate rejection reason", 2_048)
    conn = store._connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        candidate = _candidate_row(conn, candidate_id)
        prior = str(candidate["status"])
        if prior == "activated":
            raise RosterSyncError(
                "an activated candidate cannot be rejected; use rollback or retire"
            )
        if prior != "rejected":
            conn.execute(
                "UPDATE agent_candidates SET status = 'rejected' WHERE id = ?",
                (candidate_id,),
            )
            conn.execute(
                "UPDATE agent_downloads SET status = 'rejected' WHERE id = ?",
                (candidate["download_id"],),
            )
            now = store._now()
            record_candidate_status_event(
                conn,
                store,
                candidate_id,
                event_type="rejected",
                from_status=prior,
                to_status="rejected",
                reason=reason,
                created_at=now,
            )
            conn.execute(
                "INSERT INTO agent_import_events "
                "(id, event_type, agent_slug, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    store._uuid(),
                    "candidate_rejected",
                    candidate["slug"],
                    json.dumps(
                        {
                            "candidate_id": candidate_id,
                            "reason_hash": hashlib.sha256(reason.encode()).hexdigest(),
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    now,
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return candidate_comparison(store, candidate_id)


def candidate_comparison(store: Store, candidate_id: str) -> dict[str, Any]:
    """Compare candidate and active metadata without exposing prompt content."""

    conn = store._connect()
    try:
        candidate = _candidate_row(conn, candidate_id)
        active_row = conn.execute(
            "SELECT agent_slug, name, division, description, source, source_id, source_version, "
            "version, hash, categories, capabilities, tool_affinity, prompt_path, activated_at "
            "FROM agent_active WHERE agent_slug = ?",
            (candidate["slug"],),
        ).fetchone()
        active = dict(active_row) if active_row is not None else None
        if active is not None:
            for field in ("categories", "capabilities", "tool_affinity"):
                active[field] = _json_list(active.get(field), label=f"active {field}")
        fields = (
            "name",
            "division",
            "description",
            "source",
            "source_version",
            "version",
            "hash",
            "categories",
            "capabilities",
            "tool_affinity",
            "prompt_path",
        )
        changed = [
            field
            for field in fields
            if active is None or str(candidate.get(field) or "") != str(active.get(field) or "")
        ]
        events = [
            dict(row)
            for row in conn.execute(
                "SELECT event_type, from_status, to_status, reason, audit_id, created_at "
                "FROM agent_candidate_status_events WHERE candidate_id = ? "
                "ORDER BY created_at DESC, rowid DESC LIMIT 100",
                (candidate_id,),
            ).fetchall()
        ]
        return {
            "candidate": {
                "id": candidate["id"],
                "slug": candidate["slug"],
                "status": candidate["status"],
                "version": candidate["version"],
                "hash": candidate["hash"],
                "source_id": candidate["source_id"],
                "source_version": candidate["source_version"],
            },
            "active": active,
            "change": "added" if active is None else ("unchanged" if not changed else "changed"),
            "changed_fields": changed,
            "latest_audit": latest_candidate_audit_from_connection(conn, candidate_id),
            "status_history": events,
        }
    finally:
        conn.close()


__all__ = [
    "AUDIT_POLICY_HASH",
    "AUDIT_POLICY_VERSION",
    "AuditFinding",
    "CandidateRemediationEvidence",
    "InferenceAuditAssistant",
    "assert_bound_candidate_audit_from_connection",
    "assert_candidate_audits_current",
    "audit_candidate_in_connection",
    "candidate_comparison",
    "candidate_record_from_connection",
    "candidate_remediation_evidence_from_connection",
    "latest_candidate_audit_from_connection",
    "list_candidate_audits",
    "record_candidate_status_event",
    "reject_candidate",
    "run_candidate_audit",
]
