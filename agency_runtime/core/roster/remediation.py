"""Hash-bound, evidence-preserving remediation for roster source definitions."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, Literal

from agency_runtime.core.roster.source_safety import (
    contains_unsafe_source_control,
    is_unsafe_source_control,
)

REMEDIATION_SCHEMA_VERSION = 1
REMEDIATION_POLICY_REVISION = "roster-source-remediation-v1"
REMEDIATION_ATTEMPT_SCHEMA_VERSION = 1
KNOWN_ENCODING_RULE_ID = "repair-known-agency-agent-encoding"
KNOWN_ENCODING_RULE_REVISION = "1"
KNOWN_ENCODING_OPERATION = "exact_hash_bound_heading_replacements"
CONTRACT_PROJECTION_RULE_ID = "project-agency-governed-contract"
CONTRACT_PROJECTION_RULE_REVISION = "2"
CONTRACT_PROJECTION_OPERATION = "project_allowlisted_contract"
MAX_REMEDIATION_RULES = 8
MAX_REMEDIATION_EDITS = 32
MAX_REMEDIATION_OCCURRENCES = 64
MAX_REMEDIATION_FINDINGS = 64
MAX_REMEDIATION_TEXT_BYTES = 4_096

_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_RULE_TOKEN = re.compile(r"[a-z0-9][a-z0-9+._:-]{0,127}\Z")
_RULE_KINDS = frozenset({"deterministic", "semantic_projection"})
_ATTEMPT_STATUSES = frozenset(
    {
        "awaiting_registered_rule",
        "proposal_pending_review",
        "rejected_unreceipted_intermediate",
    }
)
_ATTEMPT_NEXT_ACTION = {
    "awaiting_registered_rule": "register_hash_bound_repair_and_semantic_projection",
    "proposal_pending_review": "review_deterministic_proposal_and_semantic_projection",
    "rejected_unreceipted_intermediate": "restore_immutable_source_and_verified_receipt",
}


class RosterRemediationError(ValueError):
    """Raised when remediation evidence is malformed, unsafe, or ambiguous."""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bounded_text(value: object, label: str, maximum: int = MAX_REMEDIATION_TEXT_BYTES) -> str:
    if not isinstance(value, str):
        raise RosterRemediationError(f"{label} must be text")
    if not value or len(value.encode("utf-8")) > maximum or contains_unsafe_source_control(value):
        raise RosterRemediationError(f"{label} is invalid")
    return value


def _bounded_match(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 1_024:
        raise RosterRemediationError(f"{label} is invalid")
    unsafe = {ord(character) for character in value if is_unsafe_source_control(character)}
    if unsafe - {0x04, 0x80}:
        raise RosterRemediationError(f"{label} contains a non-allowlisted control")
    return value


def _digest_text(value: object, label: str) -> str:
    text = _bounded_text(value, label, 64)
    if not _DIGEST.fullmatch(text):
        raise RosterRemediationError(f"{label} must be a SHA-256 digest")
    return text


def _finding_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or len(value) > MAX_REMEDIATION_FINDINGS:
        raise RosterRemediationError(f"{label} must be a bounded list")
    result = tuple(_bounded_text(item, f"{label} item") for item in value)
    if len(result) != len(set(result)):
        raise RosterRemediationError(f"{label} contains duplicates")
    return result


def _normalize_offsets(value: object, label: str) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)) or len(value) > MAX_REMEDIATION_OCCURRENCES:
        raise RosterRemediationError(f"{label} must be a bounded list")
    if any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in value):
        raise RosterRemediationError(f"{label} contains an invalid offset")
    result = tuple(value)
    if result != tuple(sorted(set(result))):
        raise RosterRemediationError(f"{label} must be unique and sorted")
    return result


@dataclass(frozen=True, slots=True)
class RemediationEdit:
    """One exact replacement and its offsets in the immutable source bytes."""

    match: str
    replacement: str
    occurrences: int
    byte_offsets: tuple[int, ...]

    def public_dict(self) -> dict[str, Any]:
        return {
            "match": self.match,
            "replacement": self.replacement,
            "occurrences": self.occurrences,
            "byte_offsets": list(self.byte_offsets),
        }


@dataclass(frozen=True, slots=True)
class RemediationStep:
    """One immutable transformation in a source-to-contract repair chain."""

    rule_id: str
    rule_revision: str
    kind: Literal["deterministic", "semantic_projection"]
    operation: str
    before_hash: str
    after_hash: str
    edits: tuple[RemediationEdit, ...]
    findings_resolved: tuple[str, ...]
    findings_unresolved: tuple[str, ...]

    def public_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_revision": self.rule_revision,
            "kind": self.kind,
            "operation": self.operation,
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
            "edits": [edit.public_dict() for edit in self.edits],
            "findings_resolved": list(self.findings_resolved),
            "findings_unresolved": list(self.findings_unresolved),
        }


@dataclass(frozen=True, slots=True)
class RemediationReceipt:
    """A hash-chained, versioned record of every applied repair."""

    schema_version: int
    policy_revision: str
    original_hash: str
    transformed_hash: str
    rules: tuple[RemediationStep, ...]
    findings_original: tuple[str, ...]
    findings_resolved: tuple[str, ...]
    findings_unresolved: tuple[str, ...]

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policy_revision": self.policy_revision,
            "original_hash": self.original_hash,
            "transformed_hash": self.transformed_hash,
            "rules": [rule.public_dict() for rule in self.rules],
            "findings_original": list(self.findings_original),
            "findings_resolved": list(self.findings_resolved),
            "findings_unresolved": list(self.findings_unresolved),
        }


@dataclass(frozen=True, slots=True)
class RemediationAttemptReceipt:
    """Immutable queue evidence for a repair that remains non-executable."""

    schema_version: int
    policy_revision: str
    original_hash: str
    finding: str
    attempted_rule_ids: tuple[str, ...]
    matched_rule_id: str
    proposal_hash: str
    status: str
    next_action: str
    activation_eligible: bool

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policy_revision": self.policy_revision,
            "original_hash": self.original_hash,
            "finding": self.finding,
            "attempted_rule_ids": list(self.attempted_rule_ids),
            "matched_rule_id": self.matched_rule_id,
            "proposal_hash": self.proposal_hash,
            "status": self.status,
            "next_action": self.next_action,
            "activation_eligible": self.activation_eligible,
        }


@dataclass(frozen=True, slots=True)
class _ProfileEdit:
    match: str
    replacement: str


@dataclass(frozen=True, slots=True)
class _KnownProfile:
    transformed_hash: str
    edits: tuple[_ProfileEdit, ...]


_COMMON_IDENTITY = (
    _ProfileEdit("## >à Your Identity & Memory", "## Your Identity & Memory"),
    _ProfileEdit("## <¯ Your Core Mission", "## Your Core Mission"),
    _ProfileEdit("## =¨ Critical Rules You Must Follow", "## Critical Rules You Must Follow"),
    _ProfileEdit("## =Ë Your Technical Deliverables", "## Your Technical Deliverables"),
    _ProfileEdit("## =\x04 Your Workflow Process", "## Your Workflow Process"),
    _ProfileEdit("## =Ë Your Deliverable Template", "## Your Deliverable Template"),
    _ProfileEdit("## =\x04 Learning & Memory", "## Learning & Memory"),
    _ProfileEdit("## <¯ Your Success Metrics", "## Your Success Metrics"),
    _ProfileEdit("## =\x80 Advanced Capabilities", "## Advanced Capabilities"),
)
_KNOWN_PROFILES = {
    "1a3e043f806b0b7c071d58b2ee3ab3c58c8342e2727c1ca9e6e5175f86986caf": _KnownProfile(
        "c67b433c23a8bc4f79c0e42917f10a3f4db03985eb4dd18ddc10fd57d487fbe9",
        (
            *_COMMON_IDENTITY[:6],
            _ProfileEdit("## =ñ Platform Strategy", "## Platform Strategy"),
            _ProfileEdit(
                "## <¨ Platform-Specific Implementation",
                "## Platform-Specific Implementation",
            ),
            _ProfileEdit("## ¡ Performance Optimization", "## Performance Optimization"),
            _ProfileEdit("## =' Platform Integrations", "## Platform Integrations"),
            *_COMMON_IDENTITY[6:],
        ),
    ),
    "1987be72f8fd43ca694f9145cb0dbe37eabc5b1f04439425d7b59185db9263c9": _KnownProfile(
        "d802fee2d7677278562d2b7b8a355363c6bcaab1b8492f620ecf0e7ffd04a0cc",
        (
            *_COMMON_IDENTITY[:6],
            _ProfileEdit("## <¯ ASO Objectives", "## ASO Objectives"),
            _ProfileEdit("## =\n Market Analysis", "## Market Analysis"),
            _ProfileEdit("## =ñ Optimization Strategy", "## Optimization Strategy"),
            _ProfileEdit("## =Ê Testing and Optimization", "## Testing and Optimization"),
            *_COMMON_IDENTITY[6:],
        ),
    ),
}
_KNOWN_PROFILE_OFFSETS = {
    "1a3e043f806b0b7c071d58b2ee3ab3c58c8342e2727c1ca9e6e5175f86986caf": (
        586,
        1003,
        2207,
        2869,
        11066,
        12098,
        12181,
        12679,
        13123,
        13658,
        14821,
        15564,
        15912,
    ),
    "1987be72f8fd43ca694f9145cb0dbe37eabc5b1f04439425d7b59185db9263c9": (
        624,
        1039,
        2297,
        2980,
        6813,
        7860,
        7952,
        8490,
        8911,
        9546,
        10643,
        11435,
        11837,
    ),
}
_CRLF_PROFILE_SPECS = {
    "03361c59841f74d4384902b8fd9d0aa437bb5705a305727ac936d441d2592c05": (
        "1a3e043f806b0b7c071d58b2ee3ab3c58c8342e2727c1ca9e6e5175f86986caf",
        "a15d8cc533e36c20de196e3d56cdf95b0421e432cb06332cb8ac160c2cee8b64",
        (598, 1021, 2248, 2924, 11415, 12474, 12562, 13073, 13529, 14077, 15267, 16025, 16382),
    ),
    "8c115d3c90307db0a2bc7e4e0644bdd638cb5f1e414474638c72ae483d05e053": (
        "1987be72f8fd43ca694f9145cb0dbe37eabc5b1f04439425d7b59185db9263c9",
        "bb03a63b8c1e384217daf6ad4d2c011acfc47c9b99b998247d035d99e9f504f3",
        (636, 1057, 2338, 3035, 6985, 8059, 8156, 8708, 9142, 9794, 10917, 11724, 12135),
    ),
}


def _register_reviewed_crlf_profiles() -> dict[str, str]:
    """Register exact CRLF byte variants without weakening raw-source identity."""

    canonical_hashes: dict[str, str] = {source_hash: source_hash for source_hash in _KNOWN_PROFILES}
    for source_hash, (
        canonical_hash,
        transformed_hash,
        offsets,
    ) in _CRLF_PROFILE_SPECS.items():
        canonical = _KNOWN_PROFILES[canonical_hash]
        _KNOWN_PROFILES[source_hash] = _KnownProfile(
            transformed_hash,
            tuple(
                _ProfileEdit(
                    edit.match.replace("\n", "\r\n"),
                    edit.replacement.replace("\n", "\r\n"),
                )
                for edit in canonical.edits
            ),
        )
        _KNOWN_PROFILE_OFFSETS[source_hash] = offsets
        canonical_hashes[source_hash] = canonical_hash
    return canonical_hashes


_CANONICAL_SOURCE_HASHES = _register_reviewed_crlf_profiles()


def canonical_remediation_source_hash(source_hash: str) -> str:
    """Resolve a reviewed byte-exact line-ending variant to its canonical contract."""

    normalized = str(source_hash)
    return _CANONICAL_SOURCE_HASHES.get(normalized, normalized)


def _attempt_disposition(original_hash: str) -> tuple[str, str, str]:
    profile = _KNOWN_PROFILES.get(original_hash)
    if profile is not None:
        return KNOWN_ENCODING_RULE_ID, profile.transformed_hash, "proposal_pending_review"
    if any(item.transformed_hash == original_hash for item in _KNOWN_PROFILES.values()):
        return "", "", "rejected_unreceipted_intermediate"
    return "", "", "awaiting_registered_rule"


def remediation_attempt(text: str, finding: str) -> RemediationAttemptReceipt:
    """Queue an unknown or incomplete repair without granting execution eligibility."""

    if not isinstance(text, str):
        raise TypeError("roster source text must be text")
    original_hash = _digest(text)
    matched_rule, proposal_hash, status = _attempt_disposition(original_hash)
    return RemediationAttemptReceipt(
        REMEDIATION_ATTEMPT_SCHEMA_VERSION,
        REMEDIATION_POLICY_REVISION,
        original_hash,
        _bounded_text(finding, "remediation attempt finding"),
        (KNOWN_ENCODING_RULE_ID,),
        matched_rule,
        proposal_hash,
        status,
        _ATTEMPT_NEXT_ACTION[status],
        False,
    )


def normalize_remediation_attempt(value: object) -> RemediationAttemptReceipt:
    """Validate one serialized non-executable remediation queue receipt."""

    if isinstance(value, RemediationAttemptReceipt):
        value = value.public_dict()
    expected = {
        "schema_version",
        "policy_revision",
        "original_hash",
        "finding",
        "attempted_rule_ids",
        "matched_rule_id",
        "proposal_hash",
        "status",
        "next_action",
        "activation_eligible",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise RosterRemediationError("remediation attempt fields are invalid")
    if value["schema_version"] != REMEDIATION_ATTEMPT_SCHEMA_VERSION or isinstance(
        value["schema_version"], bool
    ):
        raise RosterRemediationError("remediation attempt schema is unsupported")
    if value["policy_revision"] != REMEDIATION_POLICY_REVISION:
        raise RosterRemediationError("remediation attempt policy is unsupported")
    attempted_raw = value["attempted_rule_ids"]
    if not isinstance(attempted_raw, (list, tuple)) or (
        attempted_raw != [KNOWN_ENCODING_RULE_ID] and attempted_raw != (KNOWN_ENCODING_RULE_ID,)
    ):
        raise RosterRemediationError("remediation attempt rules are invalid")
    original_hash = _digest_text(value["original_hash"], "remediation attempt original hash")
    matched = value["matched_rule_id"]
    proposal = value["proposal_hash"]
    status = value["status"]
    if matched not in {"", KNOWN_ENCODING_RULE_ID}:
        raise RosterRemediationError("remediation attempt matched rule is invalid")
    if not isinstance(proposal, str) or (proposal and not _DIGEST.fullmatch(proposal)):
        raise RosterRemediationError("remediation attempt proposal hash is invalid")
    if status not in _ATTEMPT_STATUSES:
        raise RosterRemediationError("remediation attempt status is invalid")
    if value["next_action"] != _ATTEMPT_NEXT_ACTION[status]:
        raise RosterRemediationError("remediation attempt next action is invalid")
    expected_matched, expected_proposal, expected_status = _attempt_disposition(original_hash)
    if (matched, proposal, status) != (
        expected_matched,
        expected_proposal,
        expected_status,
    ):
        raise RosterRemediationError("remediation attempt disposition is inconsistent")
    if value["activation_eligible"] is not False:
        raise RosterRemediationError("remediation attempt cannot be activation eligible")
    return RemediationAttemptReceipt(
        REMEDIATION_ATTEMPT_SCHEMA_VERSION,
        REMEDIATION_POLICY_REVISION,
        original_hash,
        _bounded_text(value["finding"], "remediation attempt finding"),
        (KNOWN_ENCODING_RULE_ID,),
        matched,
        proposal,
        status,
        _ATTEMPT_NEXT_ACTION[status],
        False,
    )


def _normalize_edit(value: object, step_index: int, edit_index: int) -> RemediationEdit:
    if not isinstance(value, Mapping) or set(value) != {
        "match",
        "replacement",
        "occurrences",
        "byte_offsets",
    }:
        raise RosterRemediationError(
            f"remediation rule {step_index} edit {edit_index} fields are invalid"
        )
    occurrences = value["occurrences"]
    if (
        isinstance(occurrences, bool)
        or not isinstance(occurrences, int)
        or not 1 <= occurrences <= MAX_REMEDIATION_OCCURRENCES
    ):
        raise RosterRemediationError(
            f"remediation rule {step_index} edit {edit_index} occurrence count is invalid"
        )
    offsets = _normalize_offsets(
        value["byte_offsets"], f"remediation rule {step_index} edit {edit_index} offsets"
    )
    if len(offsets) != occurrences:
        raise RosterRemediationError(
            f"remediation rule {step_index} edit {edit_index} offsets do not match occurrences"
        )
    return RemediationEdit(
        _bounded_match(value["match"], f"remediation rule {step_index} edit {edit_index} match"),
        _bounded_text(
            value["replacement"],
            f"remediation rule {step_index} edit {edit_index} replacement",
            1_024,
        ),
        occurrences,
        offsets,
    )


def _normalize_step(value: object, index: int) -> RemediationStep:
    if not isinstance(value, Mapping):
        raise RosterRemediationError(f"remediation rule {index} must be an object")
    expected = {
        "rule_id",
        "rule_revision",
        "kind",
        "operation",
        "before_hash",
        "after_hash",
        "edits",
        "findings_resolved",
        "findings_unresolved",
    }
    if set(value) != expected:
        raise RosterRemediationError(f"remediation rule {index} fields are invalid")
    rule_id = _bounded_text(value["rule_id"], f"remediation rule {index} id", 128)
    revision = _bounded_text(value["rule_revision"], f"remediation rule {index} revision", 64)
    operation = _bounded_text(value["operation"], f"remediation rule {index} operation", 128)
    if not _RULE_TOKEN.fullmatch(rule_id) or not _RULE_TOKEN.fullmatch(revision):
        raise RosterRemediationError(f"remediation rule {index} identity is invalid")
    kind = _bounded_text(value["kind"], f"remediation rule {index} kind", 32)
    if kind not in _RULE_KINDS:
        raise RosterRemediationError(f"remediation rule {index} kind is invalid")
    raw_edits = value["edits"]
    if not isinstance(raw_edits, (list, tuple)) or len(raw_edits) > MAX_REMEDIATION_EDITS:
        raise RosterRemediationError(f"remediation rule {index} edits are invalid")
    edits = tuple(_normalize_edit(item, index, edit) for edit, item in enumerate(raw_edits))
    resolved = _finding_list(
        value["findings_resolved"], f"remediation rule {index} resolved findings"
    )
    unresolved = _finding_list(
        value["findings_unresolved"], f"remediation rule {index} unresolved findings"
    )
    if set(resolved) & set(unresolved):
        raise RosterRemediationError(f"remediation rule {index} finding sets overlap")
    if kind == "deterministic":
        if (
            rule_id != KNOWN_ENCODING_RULE_ID
            or revision != KNOWN_ENCODING_RULE_REVISION
            or operation != KNOWN_ENCODING_OPERATION
            or not edits
        ):
            raise RosterRemediationError("deterministic remediation rule is not allowlisted")
    elif (
        rule_id != CONTRACT_PROJECTION_RULE_ID
        or revision != CONTRACT_PROJECTION_RULE_REVISION
        or operation != CONTRACT_PROJECTION_OPERATION
        or edits
    ):
        raise RosterRemediationError("semantic remediation rule is not allowlisted")
    return RemediationStep(
        rule_id,
        revision,
        kind,  # type: ignore[arg-type]
        operation,
        _digest_text(value["before_hash"], f"remediation rule {index} before hash"),
        _digest_text(value["after_hash"], f"remediation rule {index} after hash"),
        edits,
        resolved,
        unresolved,
    )


def normalize_remediation_receipt(value: object) -> RemediationReceipt:
    """Validate and normalize a serialized remediation receipt."""

    if isinstance(value, RemediationReceipt):
        value = value.public_dict()
    if not isinstance(value, Mapping):
        raise RosterRemediationError("remediation receipt must be an object")
    expected = {
        "schema_version",
        "policy_revision",
        "original_hash",
        "transformed_hash",
        "rules",
        "findings_original",
        "findings_resolved",
        "findings_unresolved",
    }
    if set(value) != expected:
        raise RosterRemediationError("remediation receipt fields are invalid")
    if (
        isinstance(value["schema_version"], bool)
        or value["schema_version"] != REMEDIATION_SCHEMA_VERSION
    ):
        raise RosterRemediationError("remediation receipt schema is unsupported")
    if value["policy_revision"] != REMEDIATION_POLICY_REVISION:
        raise RosterRemediationError("remediation policy revision is unsupported")
    raw_rules = value["rules"]
    if not isinstance(raw_rules, (list, tuple)) or not 1 <= len(raw_rules) <= MAX_REMEDIATION_RULES:
        raise RosterRemediationError("remediation rules must be a bounded non-empty list")
    rules = tuple(_normalize_step(item, index) for index, item in enumerate(raw_rules))
    original_hash = _digest_text(value["original_hash"], "remediation original hash")
    transformed_hash = _digest_text(value["transformed_hash"], "remediation transformed hash")
    if rules[0].before_hash != original_hash or rules[-1].after_hash != transformed_hash:
        raise RosterRemediationError("remediation receipt endpoints do not match its rule chain")
    if any(left.after_hash != right.before_hash for left, right in pairwise(rules)):
        raise RosterRemediationError("remediation rule hash chain is discontinuous")
    original = _finding_list(value["findings_original"], "original remediation findings")
    resolved = _finding_list(value["findings_resolved"], "resolved remediation findings")
    unresolved = _finding_list(value["findings_unresolved"], "unresolved remediation findings")
    if (
        set(resolved) & set(unresolved)
        or set(resolved) | set(unresolved) != set(original)
        or set(rules[-1].findings_unresolved) != set(unresolved)
    ):
        raise RosterRemediationError("remediation finding disposition is inconsistent")
    known = set(original)
    for index, rule in enumerate(rules):
        if not set(rule.findings_resolved).issubset(known) or not set(
            rule.findings_unresolved
        ).issubset(known):
            raise RosterRemediationError(f"remediation rule {index} references an unknown finding")
    return RemediationReceipt(
        REMEDIATION_SCHEMA_VERSION,
        REMEDIATION_POLICY_REVISION,
        original_hash,
        transformed_hash,
        rules,
        original,
        resolved,
        unresolved,
    )


def _byte_offsets(text: str, needle: str) -> tuple[int, ...]:
    offsets: list[int] = []
    start = 0
    while (position := text.find(needle, start)) >= 0:
        offsets.append(len(text[:position].encode("utf-8")))
        start = position + len(needle)
    return tuple(offsets)


def remediate_source_text(text: str) -> tuple[str, RemediationReceipt | None]:
    """Apply an exact reviewed profile; unknown source bytes remain untouched."""

    if not isinstance(text, str):
        raise TypeError("roster source text must be text")
    original_hash = _digest(text)
    profile = _KNOWN_PROFILES.get(original_hash)
    expected_offsets = _KNOWN_PROFILE_OFFSETS.get(original_hash)
    if profile is None or expected_offsets is None or len(expected_offsets) != len(profile.edits):
        return text, None
    edits: list[RemediationEdit] = []
    transformed = text
    for specification, expected_offset in zip(profile.edits, expected_offsets, strict=True):
        offsets = _byte_offsets(text, specification.match)
        if offsets != (expected_offset,):
            return text, None
        edits.append(RemediationEdit(specification.match, specification.replacement, 1, offsets))
        transformed = transformed.replace(specification.match, specification.replacement)
    if _digest(transformed) != profile.transformed_hash or contains_unsafe_source_control(
        transformed
    ):
        return text, None
    findings = (
        "known_source_encoding_corruption",
        "unsafe_control:U+0004x2",
        "unsafe_control:U+0080x1",
    )
    step = RemediationStep(
        KNOWN_ENCODING_RULE_ID,
        KNOWN_ENCODING_RULE_REVISION,
        "deterministic",
        KNOWN_ENCODING_OPERATION,
        original_hash,
        profile.transformed_hash,
        tuple(edits),
        findings,
        (),
    )
    receipt = RemediationReceipt(
        REMEDIATION_SCHEMA_VERSION,
        REMEDIATION_POLICY_REVISION,
        original_hash,
        profile.transformed_hash,
        (step,),
        findings,
        findings,
        (),
    )
    return transformed, receipt


def is_registered_encoding_intermediate(text: str) -> bool:
    """Return whether text is a known repaired-but-not-projected source artifact."""

    if not isinstance(text, str):
        raise TypeError("roster source text must be text")
    content_hash = _digest(text)
    return any(profile.transformed_hash == content_hash for profile in _KNOWN_PROFILES.values())


def verify_known_remediation(
    original: str,
    transformed: str,
    receipt: RemediationReceipt | Mapping[str, Any],
) -> RemediationReceipt:
    """Recompute a registered repair and require byte-for-byte identical evidence."""

    normalized = normalize_remediation_receipt(receipt)
    expected_text, expected = remediate_source_text(original)
    if expected is None or expected_text != transformed or expected != normalized:
        raise RosterRemediationError("registered remediation receipt does not match source bytes")
    return normalized


def verify_packaged_remediation(
    receipt: RemediationReceipt | Mapping[str, Any],
    *,
    source_content_hash: str,
    executable_contract_hash: str,
) -> RemediationReceipt:
    """Validate a packaged two-stage receipt against the registered source profile."""

    normalized = normalize_remediation_receipt(receipt)
    profile = _KNOWN_PROFILES.get(source_content_hash)
    expected_offsets = _KNOWN_PROFILE_OFFSETS.get(source_content_hash)
    if (
        profile is None
        or expected_offsets is None
        or normalized.original_hash != source_content_hash
        or normalized.transformed_hash != executable_contract_hash
        or len(normalized.rules) != 2
        or normalized.rules[0].kind != "deterministic"
        or normalized.rules[0].after_hash != profile.transformed_hash
        or normalized.rules[1].kind != "semantic_projection"
        or normalized.findings_unresolved
        or len(normalized.rules[0].edits) != len(profile.edits)
    ):
        raise RosterRemediationError("packaged remediation is not an exact registered chain")
    for actual, expected, expected_offset in zip(
        normalized.rules[0].edits,
        profile.edits,
        expected_offsets,
        strict=True,
    ):
        if (
            actual.match != expected.match
            or actual.replacement != expected.replacement
            or actual.occurrences != 1
            or actual.byte_offsets != (expected_offset,)
        ):
            raise RosterRemediationError("packaged remediation edit is not registered")
    return normalized


def extend_with_contract_projection(
    known_receipt: RemediationReceipt | Mapping[str, Any],
    *,
    executable_contract_hash: str,
    findings_original: Sequence[str],
    findings_resolved_by_encoding: Sequence[str],
    findings_resolved_by_projection: Sequence[str],
    findings_unresolved: Sequence[str] = (),
) -> RemediationReceipt:
    """Record reviewed semantic projection after exact encoding repair."""

    known = normalize_remediation_receipt(known_receipt)
    original = tuple(findings_original)
    encoding_resolved = tuple(findings_resolved_by_encoding)
    projected_resolved = tuple(findings_resolved_by_projection)
    unresolved = tuple(findings_unresolved)
    deterministic_findings = known.findings_original
    if (
        original[: len(deterministic_findings)] != deterministic_findings
        or encoding_resolved[: len(deterministic_findings)] != deterministic_findings
    ):
        raise RosterRemediationError(
            "semantic projection must preserve every deterministic finding verbatim"
        )
    projection = RemediationStep(
        CONTRACT_PROJECTION_RULE_ID,
        CONTRACT_PROJECTION_RULE_REVISION,
        "semantic_projection",
        CONTRACT_PROJECTION_OPERATION,
        known.transformed_hash,
        _digest_text(executable_contract_hash, "executable contract hash"),
        (),
        projected_resolved,
        unresolved,
    )
    value = {
        "schema_version": REMEDIATION_SCHEMA_VERSION,
        "policy_revision": REMEDIATION_POLICY_REVISION,
        "original_hash": known.original_hash,
        "transformed_hash": projection.after_hash,
        "rules": [
            {
                **known.rules[0].public_dict(),
                "findings_resolved": list(encoding_resolved),
                "findings_unresolved": [*projected_resolved, *unresolved],
            },
            projection.public_dict(),
        ],
        "findings_original": list(original),
        "findings_resolved": [*encoding_resolved, *projected_resolved],
        "findings_unresolved": list(unresolved),
    }
    return normalize_remediation_receipt(value)


__all__ = [
    "CONTRACT_PROJECTION_OPERATION",
    "CONTRACT_PROJECTION_RULE_ID",
    "CONTRACT_PROJECTION_RULE_REVISION",
    "KNOWN_ENCODING_OPERATION",
    "KNOWN_ENCODING_RULE_ID",
    "KNOWN_ENCODING_RULE_REVISION",
    "MAX_REMEDIATION_EDITS",
    "MAX_REMEDIATION_FINDINGS",
    "MAX_REMEDIATION_OCCURRENCES",
    "MAX_REMEDIATION_RULES",
    "REMEDIATION_ATTEMPT_SCHEMA_VERSION",
    "REMEDIATION_POLICY_REVISION",
    "REMEDIATION_SCHEMA_VERSION",
    "RemediationAttemptReceipt",
    "RemediationEdit",
    "RemediationReceipt",
    "RemediationStep",
    "RosterRemediationError",
    "canonical_remediation_source_hash",
    "extend_with_contract_projection",
    "is_registered_encoding_intermediate",
    "normalize_remediation_attempt",
    "normalize_remediation_receipt",
    "remediate_source_text",
    "remediation_attempt",
    "verify_known_remediation",
    "verify_packaged_remediation",
]
