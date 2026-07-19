"""Exact-hash roster remediation, projection, and provenance tests."""

from __future__ import annotations

import copy
import gc
import hashlib
import json
import os
import tracemalloc
import unicodedata
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core.roster import bundled as bundled_subject
from agency_runtime.core.roster import ingress as ingress_subject
from agency_runtime.core.roster import remediation as subject
from agency_runtime.core.roster import review as review_subject
from agency_runtime.core.roster import semantic_projection, source_safety
from agency_runtime.core.roster import sync as sync_subject
from agency_runtime.core.roster.bundled import bundled_roster
from agency_runtime.core.roster.ingress import download_from_source
from agency_runtime.core.roster.review import audit_candidate_in_connection
from agency_runtime.core.roster.sync import (
    RosterSyncError,
    _preflight_candidate_versions,
    activate_snapshot,
    approve_snapshot,
    create_roster_diff,
    list_remediation_queue,
    list_source_scans,
    quarantine_candidate,
    quarantine_manifest_import,
    remediation_queue_snapshot,
)
from agency_runtime.core.store.sqlite import Store


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def known_profile(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    raw = (
        "---\nname: Fixture Agent\ndescription: Exact repair fixture.\n---\n"
        "## =\x04 Workflow\nDo bounded work.\n"
        "## =\x04 Memory\nDo not assume memory.\n"
        "## =\x80 Advanced\nRequire evidence.\n"
    )
    edits = (
        subject._ProfileEdit("## =\x04 Workflow", "## Workflow"),
        subject._ProfileEdit("## =\x04 Memory", "## Memory"),
        subject._ProfileEdit("## =\x80 Advanced", "## Advanced"),
    )
    repaired = raw
    for edit in edits:
        repaired = repaired.replace(edit.match, edit.replacement)
    raw_hash = _hash(raw)
    monkeypatch.setitem(
        subject._KNOWN_PROFILES,
        raw_hash,
        subject._KnownProfile(_hash(repaired), edits),
    )
    monkeypatch.setitem(
        subject._KNOWN_PROFILE_OFFSETS,
        raw_hash,
        tuple(raw.encode("utf-8").find(edit.match.encode("utf-8")) for edit in edits),
    )
    deterministic = [
        "known_source_encoding_corruption",
        "unsafe_control:U+0004x2",
        "unsafe_control:U+0080x1",
    ]
    semantic_findings = ["current_toolchain_evidence_required"]
    contract = {
        "relative_path": "engineering/fixture-agent.md",
        "slug": "fixture-agent",
        "display_name": "Fixture Agent",
        "division": "engineering",
        "description": "Exact repair fixture.",
        "categories": ["engineering", "testing"],
        "capabilities": ["review a bounded fixture"],
        "anti_capabilities": ["claim unverified completion"],
        "task_types": ["review"],
        "preferred_when": ["an exact remediation test is required"],
        "avoid_when": ["source identity or evidence is missing"],
        "required_tools": [],
        "supported_hosts": ["codex"],
        "supported_platforms": ["windows", "linux"],
        "authority": "review",
        "context_mode": "isolated_only",
        "conflicts_with": [],
        "requires": [],
        "independence_group": "testing-remediation",
        "expected_output_contract": "Return a bounded evidence-backed review.",
        "evidence_requirements": ["cite the exact source and receipt hashes"],
        "model_requirements": ["instruction-adherence"],
        "source_revision": semantic_projection.SOURCE_REVISION,
        "content_hash": raw_hash,
        "audit_revision": "2",
        "audit_status": "approved",
        "findings": [*deterministic, *semantic_findings],
        "findings_resolved_by_encoding": deterministic,
        "findings_resolved_by_projection": semantic_findings,
    }
    monkeypatch.setitem(semantic_projection._CONTRACTS, raw_hash, contract)
    return SimpleNamespace(
        raw=raw,
        repaired=repaired,
        raw_hash=raw_hash,
        contract=contract,
    )


def test_known_repair_and_projection_are_exact_idempotent_and_verifiable(known_profile) -> None:
    repaired, deterministic = subject.remediate_source_text(known_profile.raw)

    assert repaired == known_profile.repaired
    assert deterministic is not None
    assert deterministic.original_hash == known_profile.raw_hash
    assert deterministic.findings_original == (
        "known_source_encoding_corruption",
        "unsafe_control:U+0004x2",
        "unsafe_control:U+0080x1",
    )
    assert (
        subject.verify_known_remediation(
            known_profile.raw,
            repaired,
            deterministic.public_dict(),
        )
        == deterministic
    )
    assert subject.remediate_source_text(repaired) == (repaired, None)

    projected, receipt = semantic_projection.project_known_agent(
        {"slug": "fixture-agent", "name": "Fixture Agent", "division": "engineering"},
        deterministic,
        relative_path="engineering/fixture-agent.md",
    )
    prompt = semantic_projection.governed_prompt(known_profile.contract)
    assert projected["content"] == prompt
    assert receipt.findings_original == tuple(known_profile.contract["findings"])
    assert receipt.findings_resolved == tuple(known_profile.contract["findings"])
    assert not receipt.findings_unresolved
    assert (
        semantic_projection.verify_projected_remediation(
            known_profile.raw,
            prompt,
            receipt,
            relative_path="engineering/fixture-agent.md",
        )
        == receipt
    )
    assert (
        subject.verify_packaged_remediation(
            receipt,
            source_content_hash=known_profile.raw_hash,
            executable_contract_hash=_hash(prompt),
        )
        == receipt
    )


def test_reviewed_crlf_source_variant_preserves_raw_identity_and_projection(
    monkeypatch: pytest.MonkeyPatch,
    known_profile,
) -> None:
    raw = known_profile.raw.replace("\n", "\r\n")
    repaired = known_profile.repaired.replace("\n", "\r\n")
    raw_hash = _hash(raw)
    canonical = subject._KNOWN_PROFILES[known_profile.raw_hash]
    monkeypatch.setitem(
        subject._KNOWN_PROFILES,
        raw_hash,
        subject._KnownProfile(
            _hash(repaired),
            tuple(
                subject._ProfileEdit(
                    edit.match.replace("\n", "\r\n"),
                    edit.replacement.replace("\n", "\r\n"),
                )
                for edit in canonical.edits
            ),
        ),
    )
    monkeypatch.setitem(
        subject._KNOWN_PROFILE_OFFSETS,
        raw_hash,
        tuple(
            raw.encode("utf-8").find(edit.match.encode("utf-8"))
            for edit in subject._KNOWN_PROFILES[raw_hash].edits
        ),
    )
    monkeypatch.setitem(
        subject._CANONICAL_SOURCE_HASHES,
        raw_hash,
        known_profile.raw_hash,
    )

    transformed, deterministic = subject.remediate_source_text(raw)

    assert transformed == repaired
    assert deterministic is not None
    assert deterministic.original_hash == raw_hash
    assert deterministic.transformed_hash == _hash(repaired)
    projected, receipt = semantic_projection.project_known_agent(
        {
            "slug": "fixture-agent",
            "name": "Fixture Agent",
            "division": "engineering",
            "content": repaired,
        },
        deterministic,
        relative_path="engineering/fixture-agent.md",
    )
    assert receipt.original_hash == raw_hash
    assert (
        semantic_projection.verify_projected_remediation(
            raw,
            projected["content"],
            receipt,
            relative_path="engineering/fixture-agent.md",
        )
        == receipt
    )


def test_production_crlf_profiles_are_exact_reviewed_aliases() -> None:
    expected = {
        "03361c59841f74d4384902b8fd9d0aa437bb5705a305727ac936d441d2592c05": (
            "1a3e043f806b0b7c071d58b2ee3ab3c58c8342e2727c1ca9e6e5175f86986caf",
            "a15d8cc533e36c20de196e3d56cdf95b0421e432cb06332cb8ac160c2cee8b64",
        ),
        "8c115d3c90307db0a2bc7e4e0644bdd638cb5f1e414474638c72ae483d05e053": (
            "1987be72f8fd43ca694f9145cb0dbe37eabc5b1f04439425d7b59185db9263c9",
            "bb03a63b8c1e384217daf6ad4d2c011acfc47c9b99b998247d035d99e9f504f3",
        ),
    }

    for source_hash, (canonical_hash, transformed_hash) in expected.items():
        assert subject.canonical_remediation_source_hash(source_hash) == canonical_hash
        assert subject._KNOWN_PROFILES[source_hash].transformed_hash == transformed_hash
        assert semantic_projection.contract_for_source_hash(source_hash) is not None


def test_source_safety_public_projection_and_type_boundaries() -> None:
    scan = source_safety.scan_source_text("é\x04")
    assert scan.controls[0].public_dict() == {
        "codepoint": "U+0004",
        "count": 1,
        "byte_offsets": [2],
        "offsets_truncated": False,
    }
    with pytest.raises(TypeError, match="must be text"):
        source_safety.has_suspicious_source_encoding(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be text"):
        source_safety.scan_source_text(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be text"):
        source_safety.contains_unsafe_source_control(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="character must be text"):
        source_safety.is_unsafe_source_control(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="exactly one codepoint"):
        source_safety.is_unsafe_source_control("ab")


def test_source_safety_rejects_every_unicode_format_control_with_exact_offsets() -> None:
    format_controls = [
        chr(codepoint)
        for codepoint in range(0x110000)
        if unicodedata.category(chr(codepoint)) == "Cf"
    ]
    assert format_controls
    assert all(source_safety.is_unsafe_source_control(item) for item in format_controls)
    assert source_safety.contains_unsafe_source_control("visible\u202e")
    with pytest.raises(TypeError, match="scan is invalid"):
        source_safety.format_unsafe_control_finding(None)  # type: ignore[arg-type]
    assert (
        source_safety.format_unsafe_control_finding(source_safety.scan_source_text("visible")) == ""
    )

    scan = source_safety.scan_source_text("é\u202eabc\u202e")
    assert scan.controls == (source_safety.UnsafeSourceControl(0x202E, (2, 8)),)
    assert scan.controls[0].public_dict() == {
        "codepoint": "U+202E",
        "count": 2,
        "byte_offsets": [2, 8],
        "offsets_truncated": False,
    }
    assert source_safety.format_unsafe_control_finding(scan) == "unsafe_control:U+202Ex2@2|8"

    all_format_finding = source_safety.format_unsafe_control_finding(
        source_safety.scan_source_text("".join(format_controls))
    )
    assert "truncated=" in all_format_finding
    assert "evidence_sha256=" in all_format_finding

    repeated = "\u202e" * 20_000
    repeated_finding = source_safety.format_unsafe_control_finding(
        source_safety.scan_source_text(repeated)
    )
    assert repeated_finding.startswith("unsafe_control:U+202Ex20000@0|3|6|")
    assert "truncated=19984" in repeated_finding
    assert "evidence_sha256=" in repeated_finding
    assert len(repeated_finding.encode("utf-8")) < subject.MAX_REMEDIATION_TEXT_BYTES
    queued = subject.remediation_attempt(repeated, repeated_finding)
    assert queued.finding == repeated_finding
    assert queued.activation_eligible is False

    repeated_c0 = source_safety.format_unsafe_control_finding(
        source_safety.scan_source_text("\x04" * 20)
    )
    assert repeated_c0.startswith("unsafe_control:U+0004x20@0|1|2|3|4|5|6|7|8|9|10|11|12|13|14|15,")
    assert "truncated=4;evidence_sha256=" in repeated_c0

    visible = "English\t\nEspañol العربية 中文 हिन्दी 日本語 👩"
    assert source_safety.scan_source_text(visible).controls == ()
    assert source_safety.contains_unsafe_source_control(visible) is False


def test_control_evidence_commitment_is_canonical_and_max_input_memory_bounded() -> None:
    small = source_safety.scan_source_text("\u202eA\u2066B\u202e")
    canonical = bytearray(b"agency.roster.unsafe-control-evidence.v1\0")
    for codepoint, offset in ((0x202E, 0), (0x2066, 4), (0x202E, 8)):
        canonical.extend(codepoint.to_bytes(4, "big"))
        canonical.extend(offset.to_bytes(8, "big"))
    expected = hashlib.sha256(canonical).hexdigest()
    assert small.evidence_sha256 == expected
    assert source_safety._controls_evidence_hash(small.controls) == expected

    repeated = "\u202e" * (ingress_subject.MAX_AGENT_CONTENT_BYTES // 3)
    assert len(repeated.encode("utf-8")) <= ingress_subject.MAX_AGENT_CONTENT_BYTES
    gc.collect()
    tracemalloc.start()
    try:
        scan = source_safety.scan_source_text(repeated)
        finding = source_safety.format_unsafe_control_finding(scan)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert finding.startswith("unsafe_control:U+202E")
    assert "evidence_sha256=" in finding
    assert peak < 2 * 1024 * 1024


def test_control_finding_requires_well_formed_truncated_commitments() -> None:
    truncated = source_safety.UnsafeSourceControl(0x202E, (0,), total_count=2)
    with pytest.raises(ValueError, match="truncated controls require"):
        source_safety.format_unsafe_control_finding(
            source_safety.SourceSafetyScan((truncated,), False)
        )
    with pytest.raises(ValueError, match="truncated controls require"):
        source_safety.format_unsafe_control_finding(
            source_safety.SourceSafetyScan((truncated,), False, "not-a-digest")
        )
    # A truncated projection cannot recompute omitted offsets. The formatter
    # validates only the digest shape; production scans and their commitments
    # originate together in scan_source_text.
    finding = source_safety.format_unsafe_control_finding(
        source_safety.SourceSafetyScan((truncated,), False, "a" * 64)
    )
    assert finding.endswith("truncated=1;evidence_sha256=" + "a" * 64)

    complete_groups = tuple(
        source_safety.UnsafeSourceControl(codepoint, (index,))
        for index, codepoint in enumerate(
            codepoint
            for codepoint in range(0x110000)
            if unicodedata.category(chr(codepoint)) == "Cf"
        )
    )
    finding = source_safety.format_unsafe_control_finding(
        source_safety.SourceSafetyScan(complete_groups, False)
    )
    assert "truncated=" in finding
    assert "evidence_sha256=" + source_safety._controls_evidence_hash(complete_groups) in finding


def test_json_yaml_and_markdown_wrappers_cannot_hide_unicode_format_controls(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    documents = {
        "bidi-markdown.md": (
            "---\nname: Bidi Markdown\ndescription: Unsafe format control.\n---\n"
            "Visible prefix \u202e hidden suffix.\n"
        ),
        "isolate.json": json.dumps(
            {
                "name": "Isolate JSON",
                "description": "Unsafe format control.",
                "content": "Visible prefix \u2066 hidden suffix.",
            },
            ensure_ascii=False,
        ),
        "zero-width.yaml": (
            "name: Zero Width YAML\n"
            "description: Unsafe format control.\n"
            "content: Visible prefix \u200b hidden suffix.\n"
        ),
    }
    for filename, content in documents.items():
        (division / filename).write_text(content, encoding="utf-8")

    downloaded = download_from_source(str(source))
    assert downloaded == []
    assert len(downloaded.outcomes) == 3
    by_path = {Path(outcome.relative_path).name: outcome for outcome in downloaded.outcomes}
    for filename, codepoint in (
        ("bidi-markdown.md", 0x202E),
        ("isolate.json", 0x2066),
        ("zero-width.yaml", 0x200B),
    ):
        outcome = by_path[filename]
        byte_offset = (division / filename).read_bytes().find(chr(codepoint).encode("utf-8"))
        assert outcome.status == "quarantined"
        assert outcome.finding == f"unsafe_control:U+{codepoint:04X}x1@{byte_offset}"
        assert outcome.remediation_attempt is not None
        assert outcome.remediation_attempt.activation_eligible is False


def test_semantic_projection_rejects_unregistered_or_wrong_stage_evidence(
    known_profile,
) -> None:
    with pytest.raises(subject.RosterRemediationError, match="no registered semantic"):
        semantic_projection.verify_projected_candidate_contract(
            {},
            source_hash="0" * 64,
            relative_path="engineering/unknown.md",
        )
    repaired, deterministic = subject.remediate_source_text(known_profile.raw)
    assert deterministic is not None
    projected, full = semantic_projection.project_known_agent(
        {
            "slug": "fixture-agent",
            "name": "Fixture Agent",
            "division": "engineering",
            "content": repaired,
        },
        deterministic,
        relative_path="engineering/fixture-agent.md",
    )
    with pytest.raises(subject.RosterRemediationError, match="encoding-only"):
        semantic_projection.project_known_agent(
            projected,
            full,
            relative_path="engineering/fixture-agent.md",
        )
    with pytest.raises(subject.RosterRemediationError, match="no registered encoding"):
        semantic_projection.verify_projected_remediation(
            "unknown source",
            projected["content"],
            full,
            relative_path="engineering/fixture-agent.md",
        )


def test_ingress_quarantines_projection_failure_and_direct_sources_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    known_profile,
) -> None:
    accumulator = ingress_subject._DownloadAccumulator("direct-source")
    with pytest.raises(RosterSyncError, match="original-source receipt"):
        accumulator.ingest(ingress_subject._SourceDocument("repaired.md", known_profile.repaired))
    with pytest.raises(RosterSyncError, match="unsafe control"):
        accumulator.ingest(
            ingress_subject._SourceDocument("unsafe.md", "---\nname: Unsafe\n---\n\x07")
        )
    with pytest.raises(RosterSyncError, match="semantic projection"):
        ingress_subject.parse_agent_file(known_profile.repaired)
    with pytest.raises(RosterSyncError, match="semantic projection"):
        ingress_subject._normalize_agent(
            {
                "slug": "repaired-agent",
                "name": "Repaired Agent",
                "description": "Missing receipt.",
                "content": known_profile.repaired,
            }
        )

    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.raw)

    def fail_projection(*_args, **_kwargs):
        raise subject.RosterRemediationError("projection unavailable")

    monkeypatch.setattr(ingress_subject, "project_known_agent", fail_projection)
    downloaded = download_from_source(str(source))
    assert downloaded == []
    [outcome] = downloaded.outcomes
    assert outcome.status == "quarantined"
    assert outcome.remediation_attempt is not None
    assert outcome.remediation_attempt.activation_eligible is False


def _register_test_profile(
    monkeypatch: pytest.MonkeyPatch,
    raw: str,
    match: str,
    replacement: str,
) -> tuple[str, str]:
    repaired = raw.replace(match, replacement)
    raw_hash = _hash(raw)
    monkeypatch.setitem(
        subject._KNOWN_PROFILES,
        raw_hash,
        subject._KnownProfile(
            _hash(repaired),
            (subject._ProfileEdit(match, replacement),),
        ),
    )
    monkeypatch.setitem(
        subject._KNOWN_PROFILE_OFFSETS,
        raw_hash,
        (raw.encode("utf-8").find(match.encode("utf-8")),),
    )
    return raw_hash, repaired


@pytest.mark.parametrize(
    ("raw", "match", "replacement", "finding"),
    [
        ("[BROKEN", "BROKEN", "invalid", "JSON roster"),
        (
            '[{"name":"BROKEN"},{"name":"Other"}]',
            "BROKEN",
            "Fixed",
            "exactly one candidate",
        ),
        ('["BROKEN"]', "BROKEN", "Fixed", "not an object"),
    ],
)
def test_remediated_json_ingress_quarantines_ambiguous_or_invalid_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    raw: str,
    match: str,
    replacement: str,
    finding: str,
) -> None:
    _register_test_profile(monkeypatch, raw, match, replacement)
    accumulator = ingress_subject._DownloadAccumulator("json-source")
    accumulator.ingest(
        ingress_subject._SourceDocument(
            "root/engineering/json-agent.json",
            raw,
            "engineering",
            "engineering/json-agent.json",
        )
    )

    assert accumulator.candidates == []
    [outcome] = accumulator.outcomes
    assert outcome.status == "quarantined"
    assert finding in outcome.finding
    assert outcome.remediation_attempt is not None


def test_remediated_json_ingress_projects_before_candidate_eligibility(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    known_profile,
) -> None:
    raw = json.dumps(
        [
            {
                "slug": "json-agent",
                "name": "JSON Agent",
                "description": "Reviewed JSON source.",
                "division": "engineering",
                "content": "BROKEN prompt",
            }
        ],
        separators=(",", ":"),
    )
    raw_hash, _repaired = _register_test_profile(monkeypatch, raw, "BROKEN", "SAFE")
    contract = copy.deepcopy(known_profile.contract)
    contract.update(
        relative_path="engineering/json-agent.json",
        slug="json-agent",
        display_name="JSON Agent",
        description="Reviewed JSON source.",
        content_hash=raw_hash,
    )
    monkeypatch.setitem(semantic_projection._CONTRACTS, raw_hash, contract)
    accumulator = ingress_subject._DownloadAccumulator("json-source")
    accumulator.ingest(
        ingress_subject._SourceDocument(
            "root/engineering/json-agent.json",
            raw,
            "engineering",
            "engineering/json-agent.json",
        )
    )

    [candidate] = accumulator.candidates
    [outcome] = accumulator.outcomes
    assert candidate["slug"] == "json-agent"
    assert outcome.status == "candidate"
    assert outcome.remediation is not None
    assert [rule.kind for rule in outcome.remediation.rules] == [
        "deterministic",
        "semantic_projection",
    ]

    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source("json-source", "json-source")
    candidate_ids, persisted = quarantine_manifest_import(
        accumulator.candidates,
        accumulator.outcomes,
        source_id,
        store,
    )
    assert len(candidate_ids) == 1
    assert persisted[0]["source_download_id"]


def test_unknown_or_ambiguous_repairs_never_guess(
    monkeypatch: pytest.MonkeyPatch,
    known_profile,
) -> None:
    unknown = known_profile.raw + "changed"
    assert subject.remediate_source_text(unknown) == (unknown, None)
    ambiguous_hash = _hash(unknown)
    monkeypatch.setitem(
        subject._KNOWN_PROFILES,
        ambiguous_hash,
        subject._KnownProfile(
            _hash(unknown.replace("Do bounded work.", "Do safe work.")),
            (subject._ProfileEdit("missing exact marker", "replacement"),),
        ),
    )
    monkeypatch.setitem(subject._KNOWN_PROFILE_OFFSETS, ambiguous_hash, (0,))
    assert subject.remediate_source_text(unknown) == (unknown, None)


def test_remediation_attempts_queue_unknowns_and_keep_proposals_non_executable(
    known_profile,
) -> None:
    assert {
        "REMEDIATION_ATTEMPT_SCHEMA_VERSION",
        "RemediationAttemptReceipt",
        "normalize_remediation_attempt",
        "remediation_attempt",
    }.issubset(subject.__all__)
    unknown = subject.remediation_attempt("unknown source", "suspicious_source_encoding")
    assert unknown.status == "awaiting_registered_rule"
    assert unknown.matched_rule_id == ""
    assert unknown.proposal_hash == ""
    assert unknown.next_action == "register_hash_bound_repair_and_semantic_projection"
    assert unknown.activation_eligible is False
    assert subject.normalize_remediation_attempt(unknown.public_dict()) == unknown

    proposal = subject.remediation_attempt(
        known_profile.raw,
        "known source requires governed review",
    )
    assert proposal.status == "proposal_pending_review"
    assert proposal.matched_rule_id == subject.KNOWN_ENCODING_RULE_ID
    assert proposal.proposal_hash == _hash(known_profile.repaired)
    assert proposal.activation_eligible is False

    intermediate = subject.remediation_attempt(
        known_profile.repaired,
        "unreceipted_known_encoding_repair",
    )
    assert intermediate.status == "rejected_unreceipted_intermediate"
    assert intermediate.activation_eligible is False


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", True, "schema"),
        ("policy_revision", "old", "policy"),
        ("attempted_rule_ids", [], "rules"),
        ("matched_rule_id", "unknown-rule", "matched rule"),
        ("proposal_hash", "invalid", "proposal hash"),
        ("status", "approved", "status"),
        ("next_action", "activate", "next action"),
        ("activation_eligible", True, "activation eligible"),
    ],
)
def test_remediation_attempt_receipt_rejects_tamper(
    field: str,
    value: object,
    message: str,
) -> None:
    receipt = subject.remediation_attempt("unknown source", "unknown finding").public_dict()
    receipt[field] = value

    with pytest.raises(subject.RosterRemediationError, match=message):
        subject.normalize_remediation_attempt(receipt)


def test_remediation_attempt_rejects_valid_digest_forgery(known_profile) -> None:
    known = subject.remediation_attempt(
        known_profile.raw,
        "known source requires governed review",
    ).public_dict()
    known["proposal_hash"] = "f" * 64
    with pytest.raises(subject.RosterRemediationError, match="disposition"):
        subject.normalize_remediation_attempt(known)

    unknown = subject.remediation_attempt("unknown source", "unknown finding").public_dict()
    unknown.update(
        matched_rule_id=subject.KNOWN_ENCODING_RULE_ID,
        proposal_hash="e" * 64,
        status="proposal_pending_review",
        next_action="review_deterministic_proposal_and_semantic_projection",
    )
    with pytest.raises(subject.RosterRemediationError, match="disposition"):
        subject.normalize_remediation_attempt(unknown)


def test_remediation_primitive_validators_cover_every_fail_closed_boundary() -> None:
    with pytest.raises(subject.RosterRemediationError, match="must be text"):
        subject._bounded_text(None, "value")
    for value in (
        "",
        "x" * (subject.MAX_REMEDIATION_TEXT_BYTES + 1),
        "unsafe\x07",
        "unsafe\u202e",
    ):
        with pytest.raises(subject.RosterRemediationError, match="invalid"):
            subject._bounded_text(value, "value")

    for value in (None, "", "x" * 1_025):
        with pytest.raises(subject.RosterRemediationError, match="invalid"):
            subject._bounded_match(value, "match")
    with pytest.raises(subject.RosterRemediationError, match="non-allowlisted control"):
        subject._bounded_match("bad\x07", "match")
    with pytest.raises(subject.RosterRemediationError, match="non-allowlisted control"):
        subject._bounded_match("bad\u202e", "match")
    assert subject._bounded_match("allowed\x04\x80", "match") == "allowed\x04\x80"

    with pytest.raises(subject.RosterRemediationError, match="SHA-256"):
        subject._digest_text("x" * 64, "digest")

    for value in (None, ["x"] * (subject.MAX_REMEDIATION_FINDINGS + 1)):
        with pytest.raises(subject.RosterRemediationError, match="bounded list"):
            subject._finding_list(value, "findings")
    with pytest.raises(subject.RosterRemediationError, match="duplicates"):
        subject._finding_list(["duplicate", "duplicate"], "findings")

    for value in (None, list(range(subject.MAX_REMEDIATION_OCCURRENCES + 1))):
        with pytest.raises(subject.RosterRemediationError, match="bounded list"):
            subject._normalize_offsets(value, "offsets")
    for value in ([True], ["1"], [-1]):
        with pytest.raises(subject.RosterRemediationError, match="invalid offset"):
            subject._normalize_offsets(value, "offsets")
    for value in ([1, 1], [2, 1]):
        with pytest.raises(subject.RosterRemediationError, match="unique and sorted"):
            subject._normalize_offsets(value, "offsets")


def test_remediation_attempt_normalization_rejects_shape_and_finding_tamper() -> None:
    with pytest.raises(TypeError, match="must be text"):
        subject.remediation_attempt(None, "finding")  # type: ignore[arg-type]
    with pytest.raises(subject.RosterRemediationError, match="fields"):
        subject.normalize_remediation_attempt(None)

    receipt = subject.remediation_attempt("unknown", "finding").public_dict()
    missing = copy.deepcopy(receipt)
    missing.pop("finding")
    with pytest.raises(subject.RosterRemediationError, match="fields"):
        subject.normalize_remediation_attempt(missing)

    tuple_rules = copy.deepcopy(receipt)
    tuple_rules["attempted_rule_ids"] = tuple(tuple_rules["attempted_rule_ids"])
    assert subject.normalize_remediation_attempt(tuple_rules).public_dict() == receipt

    non_text_proposal = copy.deepcopy(receipt)
    non_text_proposal["proposal_hash"] = None
    with pytest.raises(subject.RosterRemediationError, match="proposal hash"):
        subject.normalize_remediation_attempt(non_text_proposal)

    bad_finding = copy.deepcopy(receipt)
    bad_finding["finding"] = "unsafe\x07"
    with pytest.raises(subject.RosterRemediationError, match="finding"):
        subject.normalize_remediation_attempt(bad_finding)


def test_serialized_remediation_receipt_validation_is_exhaustive(known_profile) -> None:
    _repaired, receipt = subject.remediate_source_text(known_profile.raw)
    assert receipt is not None
    valid = receipt.public_dict()

    invalid_cases: list[tuple[object, str]] = [(None, "must be an object")]

    missing = copy.deepcopy(valid)
    missing.pop("policy_revision")
    invalid_cases.append((missing, "fields"))

    for schema in (True, 2):
        changed = copy.deepcopy(valid)
        changed["schema_version"] = schema
        invalid_cases.append((changed, "schema"))

    changed = copy.deepcopy(valid)
    changed["policy_revision"] = "outdated"
    invalid_cases.append((changed, "policy revision"))

    for rules in (None, [], [valid["rules"][0]] * (subject.MAX_REMEDIATION_RULES + 1)):
        changed = copy.deepcopy(valid)
        changed["rules"] = rules
        invalid_cases.append((changed, "bounded non-empty"))

    for value, message in invalid_cases:
        with pytest.raises(subject.RosterRemediationError, match=message):
            subject.normalize_remediation_receipt(value)

    assert subject.normalize_remediation_receipt(receipt) == receipt


def test_remediation_edit_and_step_validation_rejects_every_unsafe_shape(known_profile) -> None:
    _repaired, receipt = subject.remediate_source_text(known_profile.raw)
    assert receipt is not None
    valid = receipt.public_dict()
    edit = valid["rules"][0]["edits"][0]
    step = valid["rules"][0]

    for value in (None, {"match": "x"}):
        with pytest.raises(subject.RosterRemediationError, match="edit 0 fields"):
            subject._normalize_edit(value, 0, 0)
    for occurrences in (True, 0, subject.MAX_REMEDIATION_OCCURRENCES + 1):
        changed = copy.deepcopy(edit)
        changed["occurrences"] = occurrences
        with pytest.raises(subject.RosterRemediationError, match="occurrence count"):
            subject._normalize_edit(changed, 0, 0)
    changed = copy.deepcopy(edit)
    changed["byte_offsets"] = []
    with pytest.raises(subject.RosterRemediationError, match="do not match occurrences"):
        subject._normalize_edit(changed, 0, 0)

    with pytest.raises(subject.RosterRemediationError, match="must be an object"):
        subject._normalize_step(None, 0)
    changed_step = copy.deepcopy(step)
    changed_step.pop("operation")
    with pytest.raises(subject.RosterRemediationError, match="fields"):
        subject._normalize_step(changed_step, 0)
    for field, value, message in (
        ("rule_id", "Bad Rule", "identity"),
        ("rule_revision", "Bad Revision", "identity"),
        ("kind", "heuristic", "kind"),
        ("edits", None, "edits"),
        ("edits", [edit] * (subject.MAX_REMEDIATION_EDITS + 1), "edits"),
    ):
        changed_step = copy.deepcopy(step)
        changed_step[field] = value
        with pytest.raises(subject.RosterRemediationError, match=message):
            subject._normalize_step(changed_step, 0)

    overlap = copy.deepcopy(step)
    overlap["findings_unresolved"] = [overlap["findings_resolved"][0]]
    with pytest.raises(subject.RosterRemediationError, match="overlap"):
        subject._normalize_step(overlap, 0)

    unregistered = copy.deepcopy(step)
    unregistered["operation"] = "other_operation"
    with pytest.raises(subject.RosterRemediationError, match="not allowlisted"):
        subject._normalize_step(unregistered, 0)

    semantic = copy.deepcopy(step)
    semantic.update(
        rule_id=subject.CONTRACT_PROJECTION_RULE_ID,
        rule_revision=subject.CONTRACT_PROJECTION_RULE_REVISION,
        kind="semantic_projection",
        operation="wrong_projection",
        edits=[],
    )
    with pytest.raises(subject.RosterRemediationError, match=r"semantic.*not allowlisted"):
        subject._normalize_step(semantic, 0)


def test_remediation_receipt_chain_and_disposition_integrity(known_profile) -> None:
    repaired, deterministic = subject.remediate_source_text(known_profile.raw)
    assert deterministic is not None
    valid = deterministic.public_dict()

    bad_endpoint = copy.deepcopy(valid)
    bad_endpoint["original_hash"] = "f" * 64
    with pytest.raises(subject.RosterRemediationError, match="endpoints"):
        subject.normalize_remediation_receipt(bad_endpoint)

    bad_disposition = copy.deepcopy(valid)
    bad_disposition["findings_resolved"] = bad_disposition["findings_resolved"][:-1]
    with pytest.raises(subject.RosterRemediationError, match="disposition"):
        subject.normalize_remediation_receipt(bad_disposition)

    unknown_finding = copy.deepcopy(valid)
    unknown_finding["rules"][0]["findings_resolved"].append("invented_finding")
    with pytest.raises(subject.RosterRemediationError, match="unknown finding"):
        subject.normalize_remediation_receipt(unknown_finding)

    _projected, projected_receipt = semantic_projection.project_known_agent(
        {"slug": "fixture-agent", "name": "Fixture Agent", "division": "engineering"},
        deterministic,
        relative_path="engineering/fixture-agent.md",
    )
    broken_chain = projected_receipt.public_dict()
    broken_chain["rules"][1]["before_hash"] = "f" * 64
    with pytest.raises(subject.RosterRemediationError, match="discontinuous"):
        subject.normalize_remediation_receipt(broken_chain)

    with pytest.raises(subject.RosterRemediationError, match="exact registered chain"):
        subject.verify_packaged_remediation(
            deterministic,
            source_content_hash=known_profile.raw_hash,
            executable_contract_hash=_hash(repaired),
        )


def test_remediation_type_and_transformed_safety_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    known_profile,
) -> None:
    with pytest.raises(TypeError, match="must be text"):
        subject.remediate_source_text(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be text"):
        subject.is_registered_encoding_intermediate(None)  # type: ignore[arg-type]

    profile = subject._KNOWN_PROFILES[known_profile.raw_hash]
    monkeypatch.setitem(
        subject._KNOWN_PROFILES,
        known_profile.raw_hash,
        subject._KnownProfile("f" * 64, profile.edits),
    )
    assert subject.remediate_source_text(known_profile.raw) == (known_profile.raw, None)

    unsafe_edits = (
        subject._ProfileEdit(profile.edits[0].match, profile.edits[0].replacement + "\x07"),
        *profile.edits[1:],
    )
    unsafe_transformed = known_profile.raw
    for edit in unsafe_edits:
        unsafe_transformed = unsafe_transformed.replace(edit.match, edit.replacement)
    monkeypatch.setitem(
        subject._KNOWN_PROFILES,
        known_profile.raw_hash,
        subject._KnownProfile(_hash(unsafe_transformed), unsafe_edits),
    )
    assert subject.remediate_source_text(known_profile.raw) == (known_profile.raw, None)

    format_edits = (
        subject._ProfileEdit(profile.edits[0].match, profile.edits[0].replacement + "\u202e"),
        *profile.edits[1:],
    )
    format_transformed = known_profile.raw
    for edit in format_edits:
        format_transformed = format_transformed.replace(edit.match, edit.replacement)
    monkeypatch.setitem(
        subject._KNOWN_PROFILES,
        known_profile.raw_hash,
        subject._KnownProfile(_hash(format_transformed), format_edits),
    )
    assert subject.remediate_source_text(known_profile.raw) == (known_profile.raw, None)


def test_registered_intermediate_cannot_bypass_semantic_projection(
    tmp_path: Path,
    known_profile,
) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.repaired)

    downloaded = download_from_source(str(source))

    assert downloaded == []
    [outcome] = downloaded.outcomes
    assert outcome.status == "quarantined"
    assert outcome.finding == "unreceipted_known_encoding_repair"


@pytest.mark.parametrize("container", ["list", "object"])
def test_registered_intermediate_in_structured_wrapper_is_quarantined(
    tmp_path: Path,
    known_profile,
    container: str,
) -> None:
    source = tmp_path / "source"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    item = {
        "slug": "fixture-agent",
        "name": "Fixture Agent",
        "description": "Wrapped repaired intermediate.",
        "content": known_profile.repaired,
    }
    payload: object = [item] if container == "list" else item
    (division / f"wrapped-{container}.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    downloaded = download_from_source(str(source))

    assert downloaded == []
    [outcome] = downloaded.outcomes
    assert outcome.status == "quarantined"
    assert outcome.finding == "unreceipted_known_encoding_repair"


def test_modified_intermediate_cannot_be_approved_without_governed_contract(
    tmp_path: Path,
    known_profile,
) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.repaired + "\nmodified\n")
    downloaded = download_from_source(str(source))
    assert [agent["slug"] for agent in downloaded] == ["fixture-agent"]
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "modified-intermediate")
    candidate_ids, _outcomes = quarantine_manifest_import(
        downloaded,
        downloaded.outcomes,
        source_id,
        store,
    )
    snapshot = create_roster_diff(store, candidate_ids=candidate_ids)

    with pytest.raises(RosterSyncError, match="audit"):
        approve_snapshot(store, snapshot["snapshot_id"])
    assert store.get_active_roster() == []


def test_registered_projection_cannot_bypass_source_bound_remediation(
    tmp_path: Path,
) -> None:
    projected = copy.deepcopy(
        next(item for item in bundled_roster() if item["slug"] == "mobile-app-builder")
    )
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source("https://example.test/roster", "untrusted-copy")
    candidate_id = quarantine_candidate(projected, source_id, store)
    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])

    with pytest.raises(RosterSyncError, match="audit"):
        approve_snapshot(store, snapshot["snapshot_id"])
    conn = store._connect()
    try:
        finding = conn.execute(
            "SELECT finding.code FROM agent_candidate_audits AS audit "
            "JOIN agent_candidate_audit_findings AS finding ON finding.audit_id = audit.id "
            "WHERE audit.candidate_id = ? AND finding.code = ? LIMIT 1",
            (candidate_id, "registered_projection_provenance_required"),
        ).fetchone()
        remediation_events = conn.execute(
            "SELECT COUNT(*) FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediated' AND agent_slug = ?",
            (projected["slug"],),
        ).fetchone()[0]
    finally:
        conn.close()
    assert finding is not None
    assert finding["code"] == "registered_projection_provenance_required"
    assert remediation_events == 0
    assert store.get_active_roster() == []


def test_legacy_passing_projection_audit_is_not_current_after_policy_upgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projected = copy.deepcopy(
        next(item for item in bundled_roster() if item["slug"] == "mobile-app-builder")
    )
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source("https://example.test/roster", "legacy-untrusted-copy")
    legacy_policy_hash = _hash("roster-candidate-audit-v1-without-source-bound-provenance")
    current_review = review_subject._deterministic_review

    def legacy_review(conn, candidate):
        findings, active_basis_hash, payload = current_review(conn, candidate)
        return (
            [
                finding
                for finding in findings
                if finding.code != "registered_projection_provenance_required"
            ],
            active_basis_hash,
            payload,
        )

    with monkeypatch.context() as legacy:
        legacy.setattr(review_subject, "AUDIT_POLICY_HASH", legacy_policy_hash)
        legacy.setattr(review_subject, "_deterministic_review", legacy_review)
        candidate_id = quarantine_candidate(projected, source_id, store)

    legacy_audit = review_subject.candidate_comparison(store, candidate_id)["latest_audit"]
    assert legacy_audit["policy_hash"] == legacy_policy_hash
    assert legacy_audit["verdict"] == "passed"
    assert legacy_audit["findings"] == []

    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])
    with pytest.raises(RosterSyncError, match="current passing audit"):
        approve_snapshot(store, snapshot["snapshot_id"])
    assert store.get_active_roster() == []


def test_direct_store_activation_rejects_registered_intermediate(
    tmp_path: Path,
    known_profile,
) -> None:
    store = Store(tmp_path / "agency.db")

    with pytest.raises(ValueError, match="semantic projection"):
        store._activate_prevalidated_agent(
            {
                "slug": "fixture-agent",
                "name": "Fixture Agent",
                "content": known_profile.repaired,
            }
        )
    assert store.get_active_roster() == []


@pytest.mark.parametrize(
    "content",
    [
        "bounded prompt\x02with C0",
        "bounded prompt\x81with C1",
        "## CafÃ©\nBounded prompt.",
        "## Broken \ufffd heading\nBounded prompt.",
    ],
)
def test_final_activation_boundaries_reject_unsafe_or_corrupt_content(
    tmp_path: Path,
    content: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    agent = {"slug": "unsafe-agent", "name": "Unsafe Agent", "content": content}

    with pytest.raises(ValueError, match=r"unsafe controls|suspicious encoding"):
        store._activate_prevalidated_agent(agent)
    conn = store._connect()
    try:
        with pytest.raises(RosterSyncError, match="unsafe or corrupt"):
            _preflight_candidate_versions(
                conn,
                [{**agent, "version": "sha256:" + "0" * 64}],
            )
    finally:
        conn.close()
    assert store.get_active_roster() == []


def test_final_activation_boundaries_reject_registered_raw_source(
    tmp_path: Path,
    known_profile,
) -> None:
    store = Store(tmp_path / "agency.db")
    with pytest.raises(ValueError, match=r"unsafe controls|suspicious encoding"):
        store._activate_prevalidated_agent(
            {
                "slug": "fixture-agent",
                "name": "Fixture Agent",
                "content": known_profile.raw,
            }
        )


def test_final_activation_boundaries_allow_legitimate_accents_and_opaque_identity(
    tmp_path: Path,
) -> None:
    content = "## À propos\nÉquipe mobile — bounded review."
    store = Store(tmp_path / "agency.db")
    agent = {
        "slug": "accented-agent",
        "name": "Accented Agent",
        "content": content,
        "hash": "opaque-upstream-revision-7",
    }

    store._activate_prevalidated_agent(agent)
    conn = store._connect()
    try:
        assert (
            _preflight_candidate_versions(
                conn,
                [{**agent, "version": "sha256:" + "1" * 64}],
            )
            == set()
        )
    finally:
        conn.close()
    assert [item["agent_slug"] for item in store.get_active_roster()] == ["accented-agent"]


def test_direct_store_rejects_mismatched_digest_identity_without_writes(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")

    with pytest.raises(ValueError, match="does not match"):
        store._activate_prevalidated_agent(
            {
                "slug": "digest-mismatch",
                "name": "Digest Mismatch",
                "content": "safe governed prompt",
                "hash": "0" * 64,
            }
        )
    assert store.get_active_roster() == []


@pytest.mark.parametrize(
    ("slug", "field", "value"),
    [
        ("app-store-optimizer", "authority", "approve"),
        ("app-store-optimizer", "capabilities", ["mutate production listings"]),
        ("code-reviewer", "authority", "approve"),
        ("technical-writer", "capabilities", ["publish unreviewed claims"]),
    ],
)
def test_direct_store_rejects_real_bundled_contract_metadata_tamper(
    tmp_path: Path,
    slug: str,
    field: str,
    value: object,
) -> None:
    agent = copy.deepcopy(next(item for item in bundled_roster() if item["slug"] == slug))
    agent[field] = value
    store = Store(tmp_path / "agency.db")

    with pytest.raises(ValueError, match="bundled roster contract"):
        store._activate_prevalidated_agent(agent)
    assert store.get_active_roster() == []


def test_direct_store_rejects_known_bundled_slug_prompt_replacement(tmp_path: Path) -> None:
    agent = copy.deepcopy(
        next(item for item in bundled_roster() if item["slug"] == "code-reviewer")
    )
    agent["prompt_body"] = "Safe-looking but unaudited replacement."
    store = Store(tmp_path / "agency.db")

    with pytest.raises(ValueError, match="bundled roster contract"):
        store._activate_prevalidated_agent(agent)
    assert store.get_active_roster() == []


@pytest.mark.parametrize("slug", ["Code-Reviewer", " code-reviewer "])
def test_direct_store_normalizes_before_reserved_slug_validation(
    tmp_path: Path,
    slug: str,
) -> None:
    store = Store(tmp_path / "agency.db")

    with pytest.raises(ValueError, match="bundled roster contract"):
        store._activate_prevalidated_agent(
            {
                "slug": slug,
                "name": "Shadow Reviewer",
                "content": "Safe-looking arbitrary replacement.",
            }
        )
    assert store.get_active_roster() == []


def test_direct_store_persists_one_canonical_custom_slug_identity(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(
        {"slug": "My-Agent", "name": "First", "content": "First prompt."}
    )
    store._activate_prevalidated_agent(
        {
            "slug": " my-agent ",
            "name": "Second",
            "version": "2.0.0",
            "content": "Second prompt.",
        }
    )
    store._activate_prevalidated_agent(
        {"slug": "my_agent", "name": "Underscore", "content": "Third prompt."}
    )
    store._activate_prevalidated_agent(
        {"slug": "my.agent", "name": "Dot", "content": "Fourth prompt."}
    )

    active = store.get_active_roster()
    assert [item["agent_slug"] for item in active] == ["my-agent", "my.agent", "my_agent"]
    assert next(item for item in active if item["agent_slug"] == "my-agent")["name"] == "Second"


@pytest.mark.parametrize("status", ["quarantined", "retired"])
def test_direct_store_reserves_inactive_bundled_manifest_slugs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
) -> None:
    manifest = bundled_subject.bundled_manifest()
    inactive = copy.deepcopy(manifest["agents"][0])
    inactive["slug"] = f"future-{status}-specialist"
    inactive["audit_status"] = status
    manifest["agents"].append(inactive)
    monkeypatch.setattr(bundled_subject, "_validated_manifest", lambda: manifest)
    bundled_subject._bundled_contract_index.cache_clear()
    store = Store(tmp_path / "agency.db")
    try:
        with pytest.raises(ValueError, match="bundled roster contract"):
            store._activate_prevalidated_agent(
                {
                    "slug": inactive["slug"],
                    "name": "Inactive Specialist",
                    "content": "Safe-looking custom prompt.",
                }
            )
    finally:
        bundled_subject._bundled_contract_index.cache_clear()
    assert store.get_active_roster() == []


def test_projection_rejects_lost_findings_identity_and_tampering(known_profile) -> None:
    repaired, deterministic = subject.remediate_source_text(known_profile.raw)
    assert deterministic is not None
    with pytest.raises(subject.RosterRemediationError, match="preserve every"):
        subject.extend_with_contract_projection(
            deterministic,
            executable_contract_hash="0" * 64,
            findings_original=["semantic-only"],
            findings_resolved_by_encoding=[],
            findings_resolved_by_projection=["semantic-only"],
        )
    with pytest.raises(subject.RosterRemediationError, match="source identity"):
        semantic_projection.project_known_agent(
            {"slug": "wrong", "name": "Fixture Agent", "division": "engineering"},
            deterministic,
            relative_path="engineering/fixture-agent.md",
        )

    _projected, receipt = semantic_projection.project_known_agent(
        {"slug": "fixture-agent", "name": "Fixture Agent", "division": "engineering"},
        deterministic,
        relative_path="engineering/fixture-agent.md",
    )
    tampered = copy.deepcopy(receipt.public_dict())
    tampered["rules"][0]["edits"][0]["replacement"] = "## Tampered"
    with pytest.raises(subject.RosterRemediationError, match="edit is not registered"):
        subject.verify_packaged_remediation(
            tampered,
            source_content_hash=known_profile.raw_hash,
            executable_contract_hash=receipt.transformed_hash,
        )
    offset_tamper = copy.deepcopy(receipt.public_dict())
    offset_tamper["rules"][0]["edits"][0]["byte_offsets"][0] += 1
    with pytest.raises(subject.RosterRemediationError, match="edit is not registered"):
        subject.verify_packaged_remediation(
            offset_tamper,
            source_content_hash=known_profile.raw_hash,
            executable_contract_hash=receipt.transformed_hash,
        )
    with pytest.raises(subject.RosterRemediationError, match="does not match artifacts"):
        semantic_projection.verify_projected_remediation(
            known_profile.raw,
            "tampered prompt",
            receipt,
            relative_path="engineering/fixture-agent.md",
        )
    with pytest.raises(subject.RosterRemediationError, match="does not match source bytes"):
        subject.verify_known_remediation(known_profile.raw, repaired + "tampered", deterministic)


def _write_known_manifest(root: Path, raw: str) -> None:
    division = root / "engineering"
    division.mkdir(parents=True)
    (root / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    (division / "fixture-agent.md").write_bytes(raw.encode("utf-8"))


def _unknown_remediation_store(root: Path) -> Store:
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        root.chmod(0o700)
    source = root / "source"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    (division / "unknown-encoding.md").write_text(
        "---\nname: Unknown Encoding\ndescription: Must remain quarantined.\n---\n"
        "## Broken\x07 heading\nNo repair may be guessed.\n",
        encoding="utf-8",
    )
    downloaded = download_from_source(str(source))
    store = Store(root / "agency.db")
    source_id = store.add_agent_source(str(source), f"queue-{root.name}")
    quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)
    return store


def _mutate_remediation_event(store: Store, mutation) -> None:
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT id, detail FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediation_queued'"
        ).fetchone()
        detail = json.loads(row["detail"])
        mutation(conn, detail, row)
        conn.execute(
            "UPDATE agent_import_events SET detail = ? WHERE id = ?",
            (json.dumps(detail, sort_keys=True, separators=(",", ":")), row["id"]),
        )
        conn.commit()
    finally:
        conn.close()


def test_ingestion_persists_original_and_projected_artifacts_idempotently(
    tmp_path: Path,
    known_profile,
) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.raw)
    downloaded = download_from_source(str(source))

    assert [agent["slug"] for agent in downloaded] == ["fixture-agent"]
    [outcome] = downloaded.outcomes
    assert outcome.status == "candidate"
    assert outcome.content_hash == known_profile.raw_hash
    assert outcome.source_content == known_profile.raw
    assert outcome.remediation is not None
    assert outcome.remediation.rules[-1].kind == "semantic_projection"

    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "known-remediation")
    first = quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)
    second = quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)
    assert second == first

    conn = store._connect()
    try:
        rows = conn.execute(
            "SELECT status, content, hash FROM agent_downloads ORDER BY status"
        ).fetchall()
        event = conn.execute(
            "SELECT detail FROM agent_import_events WHERE event_type = 'manifest_entry_remediated'"
        ).fetchone()
    finally:
        conn.close()
    assert len(rows) == 2
    original = next(row for row in rows if row["hash"] == known_profile.raw_hash)
    assert original["content"] == known_profile.raw
    assert original["hash"] == known_profile.raw_hash
    details = json.loads(event["detail"])
    assert details["receipt"] == outcome.remediation.public_dict()
    assert details["source_download_id"] == first[1][0]["source_download_id"]


def test_unknown_quarantine_enters_bounded_remediation_queue_idempotently(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    raw = (
        "---\nname: Unknown Encoding\ndescription: Must remain quarantined.\n---\n"
        "## Broken\x07 heading\nNo repair may be guessed.\n"
    )
    (division / "unknown-encoding.md").write_text(raw, encoding="utf-8")
    downloaded = download_from_source(str(source))
    [outcome] = downloaded.outcomes
    assert outcome.status == "quarantined"
    assert outcome.remediation_attempt is not None
    assert outcome.remediation_attempt.status == "awaiting_registered_rule"
    assert outcome.remediation_attempt.activation_eligible is False

    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "unknown-remediation-queue")
    first = quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)
    second = quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)
    assert second == first
    [queued] = list_remediation_queue(store)
    assert queued["slug"] == "unknown-encoding"
    assert queued["receipt"] == outcome.remediation_attempt.public_dict()
    assert queued["receipt"]["activation_eligible"] is False

    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_import_events "
                "WHERE event_type = 'manifest_entry_remediation_queued'"
            ).fetchone()[0]
            == 1
        )
    finally:
        conn.close()


def test_remediation_queue_pages_without_loading_unbounded_history(tmp_path: Path) -> None:
    source = tmp_path / "source"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    for index in range(3):
        (division / f"unsafe-{index}.md").write_text(
            "---\n"
            f"name: Unsafe {index}\n"
            "description: Must remain quarantined.\n"
            "---\n"
            f"Broken\x07 definition {index}.\n",
            encoding="utf-8",
        )
    downloaded = download_from_source(str(source))
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "paged-remediation")
    quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)

    first = remediation_queue_snapshot(store, limit=1)
    assert first["schema_version"] == "agency.roster.remediation_queue.v2"
    assert first["pending_count"] == 3
    assert len(first["pending"]) == 1
    assert first["pending_has_more"] is True
    assert first["next_pending_cursor"] == first["pending"][0]["event_id"]
    assert first["history"] == []
    assert first["history_count"] == 0

    second = remediation_queue_snapshot(
        store,
        limit=1,
        pending_cursor=first["next_pending_cursor"],
    )
    third = remediation_queue_snapshot(
        store,
        limit=1,
        pending_cursor=second["next_pending_cursor"],
    )
    event_ids = {
        first["pending"][0]["event_id"],
        second["pending"][0]["event_id"],
        third["pending"][0]["event_id"],
    }
    assert len(event_ids) == 3
    assert second["pending_has_more"] is True
    assert third["pending_has_more"] is False
    assert third["next_pending_cursor"] == ""

    with pytest.raises(ValueError, match="does not identify"):
        remediation_queue_snapshot(store, pending_cursor="not-an-event")


def test_large_resolution_history_uses_expression_index_for_pending_lookup(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "resolution-plan.db")
    conn = store._connect()
    try:
        queue_rows = [
            (
                f"queue-{index}",
                "manifest_entry_remediation_queued",
                f"agent-{index}",
                "{}",
                "2026-07-18T00:00:00+00:00",
            )
            for index in range(2_000)
        ]
        resolution_rows = [
            (
                f"resolution-{index}",
                "manifest_entry_remediation_resolved",
                f"agent-{index}",
                json.dumps(
                    {"queue_event_id": f"queue-{index}"},
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "2026-07-18T00:00:01+00:00",
            )
            for index in range(2_000)
        ]
        conn.executemany(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [*queue_rows, *resolution_rows],
        )
        conn.commit()
        bounded_resolution_detail = (
            sync_subject.BOUNDED_REMEDIATION_EVENT_DETAIL_PREDICATE_SQL.replace(
                "detail",
                "resolution.detail",
            )
        )
        query = (
            "SELECT resolution.id "
            "FROM agent_import_events AS resolution "
            "INDEXED BY idx_agent_import_resolution_queue "
            "WHERE resolution.event_type = 'manifest_entry_remediation_resolved' "
            f"AND {bounded_resolution_detail} "
            "AND json_extract(resolution.detail, '$.queue_event_id') = ? "
            "ORDER BY resolution.event_sequence LIMIT 3"
        )
        plan = [
            str(row["detail"])
            for row in conn.execute(
                "EXPLAIN QUERY PLAN " + query,
                ("queue-1999",),
            ).fetchall()
        ]
        assert [row["id"] for row in conn.execute(query, ("queue-1999",)).fetchall()] == [
            "resolution-1999"
        ]
    finally:
        conn.close()

    assert any(
        "SEARCH resolution USING INDEX idx_agent_import_resolution_queue" in detail
        for detail in plan
    ), plan
    assert not any("SCAN resolution" in detail for detail in plan)


def _superseded_remediation_store(root: Path) -> Store:
    source = root / "source"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    definition = division / "evolving-agent.json"
    definition.write_text(
        '{"name":"Evolving Agent","description":"Initially unsafe",'
        '"content":"Broken\x07 definition."}',
        encoding="utf-8",
    )
    store = Store(root / "agency.db")
    source_id = store.add_agent_source(str(source), "evolving-remediation")
    first = download_from_source(str(source))
    quarantine_manifest_import(first, first.outcomes, source_id, store)

    definition.write_text(
        json.dumps(
            {
                "slug": "evolving-agent",
                "name": "Evolving Agent",
                "description": "Safe replacement.",
                "division": "engineering",
                "categories": ["engineering", "testing"],
                "capabilities": ["perform bounded fixture work"],
                "anti_capabilities": ["claim unverified completion"],
                "task_types": ["review"],
                "preferred_when": ["the bounded fixture matches"],
                "avoid_when": ["required evidence is unavailable"],
                "required_tools": [],
                "tool_affinity": [],
                "supported_hosts": ["codex"],
                "supported_platforms": ["linux", "windows"],
                "authority": "review",
                "context_mode": "isolated_only",
                "conflicts_with": [],
                "requires": [],
                "independence_group": "fixture-evolving-agent",
                "expected_output_contract": "Return bounded evidence-backed output.",
                "evidence_requirements": ["cite the fixture result"],
                "model_requirements": ["instruction-adherence"],
                "source_revision": "test-revision",
                "audit_revision": "test",
                "audit_status": "approved",
                "findings": [],
                "prompt_body": "Perform bounded work and return evidence.",
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    second = download_from_source(str(source))
    quarantine_manifest_import(second, second.outcomes, source_id, store)
    quarantine_manifest_import(second, second.outcomes, source_id, store)
    return store


def test_changed_source_resolves_queue_once_and_reingestion_is_idempotent(
    tmp_path: Path,
) -> None:
    store = _superseded_remediation_store(tmp_path)
    snapshot = remediation_queue_snapshot(store)
    assert snapshot["pending"] == []
    assert snapshot["pending_count"] == 0
    assert snapshot["history_count"] == 1
    assert snapshot["history"][0]["resolution"] == "superseded_by_candidate"
    assert snapshot["history"][0]["source_hash"] != snapshot["history"][0]["original_hash"]
    assert len(list_source_scans(store)) == 2

    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_import_events "
                "WHERE event_type = 'manifest_entry_remediation_resolved'"
            ).fetchone()[0]
            == 1
        )
    finally:
        conn.close()


def test_registered_rule_resolves_exact_source_with_two_stage_proof(
    tmp_path: Path,
    known_profile,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.raw)
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "registered-remediation")

    with monkeypatch.context() as patch:
        patch.setattr(
            ingress_subject,
            "remediate_source_text",
            lambda content: (content, None),
        )
        first = download_from_source(str(source))
    assert first.outcomes[0].status == "quarantined"
    quarantine_manifest_import(first, first.outcomes, source_id, store)

    second = download_from_source(str(source))
    assert second.outcomes[0].status == "candidate"
    assert second.outcomes[0].remediation is not None
    quarantine_manifest_import(second, second.outcomes, source_id, store)
    quarantine_manifest_import(second, second.outcomes, source_id, store)

    snapshot = remediation_queue_snapshot(store)
    assert snapshot["pending_count"] == 0
    assert snapshot["history_count"] == 1
    [resolved] = snapshot["history"]
    assert resolved["resolution"] == "remediated_candidate"
    assert resolved["source_hash"] == known_profile.raw_hash
    assert resolved["original_hash"] == known_profile.raw_hash

    conn = store._connect()
    try:
        event_counts = {
            row["event_type"]: row["count"]
            for row in conn.execute(
                "SELECT event_type, COUNT(*) AS count FROM agent_import_events "
                "WHERE event_type IN ('manifest_entry_remediated', "
                "'manifest_entry_remediation_resolved') GROUP BY event_type"
            ).fetchall()
        }
    finally:
        conn.close()
    assert event_counts == {
        "manifest_entry_remediated": 1,
        "manifest_entry_remediation_resolved": 1,
    }

    conn = store._connect()
    try:
        event = conn.execute(
            "SELECT id, agent_slug, detail, created_at FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediated'"
        ).fetchone()
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                "duplicate-remediation-proof",
                "manifest_entry_remediated",
                event["agent_slug"],
                event["detail"],
                event["created_at"],
            ),
        )
        conn.commit()
    finally:
        conn.close()
    ambiguous = remediation_queue_snapshot(store)
    assert ambiguous["pending_count"] == 1
    assert ambiguous["history_count"] == 0
    assert ambiguous["unvalidated_resolution_count"] == 1

    conn = store._connect()
    try:
        conn.execute("DELETE FROM agent_import_events WHERE id = 'duplicate-remediation-proof'")
        detail = json.loads(event["detail"])
        detail["receipt"]["transformed_hash"] = "f" * 64
        conn.execute(
            "UPDATE agent_import_events SET detail = ? WHERE id = ?",
            (json.dumps(detail, sort_keys=True, separators=(",", ":")), event["id"]),
        )
        conn.commit()
    finally:
        conn.close()
    tampered = remediation_queue_snapshot(store)
    assert tampered["pending_count"] == 1
    assert tampered["history_count"] == 0
    assert tampered["unvalidated_resolution_count"] == 1


def test_queue_path_origin_and_scan_header_tamper_fail_closed(tmp_path: Path) -> None:
    store = _unknown_remediation_store(tmp_path)
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT id, detail FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediation_queued'"
        ).fetchone()
        detail = json.loads(row["detail"])
        detail["origin"] += ".forged"
        detail["binding_hash"] = sync_subject._remediation_queue_binding_hash(
            source_id=detail["source_id"],
            scan_id=detail["scan_id"],
            relative_path=detail["relative_path"],
            origin=detail["origin"],
            content_hash=detail["receipt"]["original_hash"],
        )
        conn.execute(
            "UPDATE agent_import_events SET detail = ? WHERE id = ?",
            (json.dumps(detail, sort_keys=True, separators=(",", ":")), row["id"]),
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RosterSyncError, match=r"source scan .* integrity"):
        list_remediation_queue(store)

    store = _unknown_remediation_store(tmp_path / "header")
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT id, detail FROM agent_import_events WHERE event_type = 'source_scan_recorded'"
        ).fetchone()
        detail = json.loads(row["detail"])
        detail["manifest_hash"] = "f" * 64
        conn.execute(
            "UPDATE agent_import_events SET detail = ? WHERE id = ?",
            (json.dumps(detail, sort_keys=True, separators=(",", ":")), row["id"]),
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RosterSyncError, match="receipt header"):
        list_remediation_queue(store)


def _reappend_import_event_after_scan_header(store: Store, event_type: str) -> None:
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT id, event_type, agent_slug, detail, created_at "
            "FROM agent_import_events WHERE event_type = ?",
            (event_type,),
        ).fetchone()
        assert row is not None
        values = tuple(row)
        conn.execute("DELETE FROM agent_import_events WHERE id = ?", (row["id"],))
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            values,
        )
        conn.commit()
    finally:
        conn.close()


def test_scan_provenance_order_rejects_nonpositive_sequence() -> None:
    with pytest.raises(RosterSyncError, match="does not precede its source scan header"):
        sync_subject._assert_scan_provenance_precedes_header(
            event_order=0,
            event_created_at="2026-07-18T00:00:00+00:00",
            header_order=1,
            scan_created_at="2026-07-18T00:00:00+00:00",
            label="forged provenance",
        )


def test_quarantine_provenance_must_precede_source_scan_header(tmp_path: Path) -> None:
    store = _unknown_remediation_store(tmp_path)
    _reappend_import_event_after_scan_header(
        store,
        "manifest_entry_remediation_queued",
    )

    with pytest.raises(RosterSyncError, match="does not precede its source scan header"):
        list_remediation_queue(store)


def test_ignored_provenance_must_precede_source_scan_header(tmp_path: Path) -> None:
    source = tmp_path / "source"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    (division / "notes.md").write_text(
        "# Not an agent definition\n",
        encoding="utf-8",
    )
    downloaded = download_from_source(str(source))
    assert [outcome.status for outcome in downloaded.outcomes] == ["ignored"]
    store = Store(tmp_path / "ignored-order.db")
    source_id = store.add_agent_source(str(source), "ignored-order")
    quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)
    _reappend_import_event_after_scan_header(store, "manifest_entry_ignored")

    with pytest.raises(RosterSyncError, match="does not precede its source scan header"):
        list_source_scans(store)


def test_candidate_transformation_must_precede_source_scan_header(
    tmp_path: Path,
    known_profile,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.raw)
    store = Store(tmp_path / "candidate-order.db")
    source_id = store.add_agent_source(str(source), "candidate-order")
    with monkeypatch.context() as patch:
        patch.setattr(
            ingress_subject,
            "remediate_source_text",
            lambda content: (content, None),
        )
        first = download_from_source(str(source))
    quarantine_manifest_import(first, first.outcomes, source_id, store)
    second = download_from_source(str(source))
    quarantine_manifest_import(second, second.outcomes, source_id, store)
    _reappend_import_event_after_scan_header(store, "manifest_entry_remediated")

    with pytest.raises(RosterSyncError, match="does not precede its source scan header"):
        list_source_scans(store)


def test_duplicate_or_malformed_resolution_events_fail_closed(tmp_path: Path) -> None:
    store = _superseded_remediation_store(tmp_path)
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT agent_slug, detail, created_at FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediation_resolved'"
        ).fetchone()
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                "duplicate-resolution",
                "manifest_entry_remediation_resolved",
                row["agent_slug"],
                row["detail"],
                row["created_at"],
            ),
        )
        conn.commit()
    finally:
        conn.close()
    duplicate = remediation_queue_snapshot(store)
    assert duplicate["pending_count"] == 0
    assert duplicate["history_count"] == 1
    assert duplicate["unvalidated_resolution_count"] == 1

    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_import_events SET detail = '{' "
            "WHERE event_type = 'manifest_entry_remediation_resolved'"
        )
        conn.commit()
    finally:
        conn.close()
    snapshot = remediation_queue_snapshot(store)
    assert snapshot["pending_count"] == 1
    assert snapshot["history_count"] == 0
    assert snapshot["unvalidated_resolution_count"] == 2


def test_missing_authority_edge_reopens_pending_and_survives_vacuum(
    tmp_path: Path,
) -> None:
    store = _superseded_remediation_store(tmp_path)
    conn = store._connect()
    try:
        before = [
            tuple(row)
            for row in conn.execute(
                "SELECT id, event_sequence FROM agent_import_events ORDER BY event_sequence"
            ).fetchall()
        ]
        dependency = conn.execute(
            "SELECT resolution_event_id, dependency_kind, dependency_id "
            "FROM agent_remediation_resolution_dependencies "
            "WHERE dependency_kind = 'candidate_audit'"
        ).fetchone()
        assert dependency is not None
        conn.execute(
            "DELETE FROM agent_remediation_resolution_dependencies "
            "WHERE resolution_event_id = ? AND dependency_kind = ? AND dependency_id = ?",
            tuple(dependency),
        )
        conn.commit()
    finally:
        conn.close()

    reopened = remediation_queue_snapshot(store)
    assert reopened["pending_count"] == 1
    assert reopened["history_count"] == 0
    assert reopened["unvalidated_resolution_count"] == 1

    conn = store._connect()
    try:
        conn.execute("VACUUM")
        after = [
            tuple(row)
            for row in conn.execute(
                "SELECT id, event_sequence FROM agent_import_events ORDER BY event_sequence"
            ).fetchall()
        ]
    finally:
        conn.close()
    assert after == before
    assert remediation_queue_snapshot(store)["pending_count"] == 1


def test_ambiguous_raw_resolution_duplicates_cannot_block_canonical_authority(
    tmp_path: Path,
) -> None:
    store = _superseded_remediation_store(tmp_path)
    downloaded = download_from_source(str(tmp_path / "source"))
    conn = store._connect()
    try:
        source_id = conn.execute("SELECT id FROM agent_sources").fetchone()["id"]
        resolution = conn.execute(
            "SELECT id, agent_slug, detail, created_at FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediation_resolved'"
        ).fetchone()
        assert resolution is not None
        conn.execute("DELETE FROM agent_import_events WHERE id = ?", (resolution["id"],))
        conn.executemany(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    f"raw-duplicate-{index}",
                    "manifest_entry_remediation_resolved",
                    resolution["agent_slug"],
                    resolution["detail"],
                    resolution["created_at"],
                )
                for index in range(2)
            ],
        )
        conn.commit()
    finally:
        conn.close()

    before = remediation_queue_snapshot(store)
    assert before["pending_count"] == 1
    assert before["history_count"] == 0
    assert before["unvalidated_resolution_count"] == 2

    quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)
    after = remediation_queue_snapshot(store)
    assert after["pending_count"] == 0
    assert after["history_count"] == 1
    assert after["unvalidated_resolution_count"] == 2
    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_import_events "
                "WHERE event_type = 'manifest_entry_remediation_resolved'"
            ).fetchone()[0]
            == 3
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM agent_remediation_resolution_authority").fetchone()[
                0
            ]
            == 1
        )
    finally:
        conn.close()


def test_authority_persistence_failure_rolls_back_candidate_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    definition = division / "rollback-agent.json"
    definition.write_text(
        '{"name":"Rollback Agent","description":"Initially unsafe",'
        '"content":"Broken\x07 definition."}',
        encoding="utf-8",
    )
    store = Store(tmp_path / "rollback.db")
    source_id = store.add_agent_source(str(source), "rollback-remediation")
    first = download_from_source(str(source))
    quarantine_manifest_import(first, first.outcomes, source_id, store)
    definition.write_text(
        json.dumps(
            {
                "slug": "rollback-agent",
                "name": "Rollback Agent",
                "description": "Safe replacement.",
                "division": "engineering",
                "categories": ["engineering", "testing"],
                "capabilities": ["perform bounded fixture work"],
                "anti_capabilities": ["claim unverified completion"],
                "task_types": ["review"],
                "preferred_when": ["the bounded fixture matches"],
                "avoid_when": ["required evidence is unavailable"],
                "required_tools": [],
                "tool_affinity": [],
                "supported_hosts": ["codex"],
                "supported_platforms": ["linux", "windows"],
                "authority": "review",
                "context_mode": "isolated_only",
                "conflicts_with": [],
                "requires": [],
                "independence_group": "fixture-rollback-agent",
                "expected_output_contract": "Return bounded evidence-backed output.",
                "evidence_requirements": ["cite the fixture result"],
                "model_requirements": ["instruction-adherence"],
                "source_revision": "test-revision",
                "audit_revision": "test",
                "audit_status": "approved",
                "findings": [],
                "prompt_body": "Perform bounded work and return evidence.",
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    second = download_from_source(str(source))

    def fail_authority(*_args, **_kwargs) -> None:
        raise RosterSyncError("injected authority persistence failure")

    monkeypatch.setattr(
        sync_subject,
        "_persist_remediation_resolution_authority",
        fail_authority,
    )
    with pytest.raises(RosterSyncError, match="injected authority persistence failure"):
        quarantine_manifest_import(second, second.outcomes, source_id, store)

    snapshot = remediation_queue_snapshot(store)
    assert snapshot["pending_count"] == 1
    assert snapshot["history_count"] == 0
    assert snapshot["unvalidated_resolution_count"] == 0
    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_import_events "
                "WHERE event_type = 'manifest_entry_remediation_resolved'"
            ).fetchone()[0]
            == 0
        )
        assert conn.execute("SELECT COUNT(*) FROM agent_candidates").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM agent_source_scans").fetchone()[0] == 1
    finally:
        conn.close()


def test_remediation_queue_rejects_event_or_download_tamper(tmp_path: Path) -> None:
    source = tmp_path / "source"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    raw = (
        "---\nname: Unsafe Control\ndescription: Must remain quarantined.\n---\n"
        "## Broken\x07 heading\n"
    )
    (division / "unsafe-control.md").write_bytes(raw.encode("utf-8"))
    downloaded = download_from_source(str(source))
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "tamper-remediation-queue")
    quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)

    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_import_events SET detail = '{}' "
            "WHERE event_type = 'manifest_entry_remediation_queued'"
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RosterSyncError, match="quarantine evidence"):
        quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)
    with pytest.raises(RosterSyncError, match="remediation queue event fields"):
        list_remediation_queue(store)


@pytest.mark.parametrize("limit", [True, "1", 0, 1_001])
def test_remediation_queue_limit_is_strict(tmp_path: Path, limit: object) -> None:
    with pytest.raises(ValueError, match="between 1 and 1000"):
        list_remediation_queue(Store(tmp_path / "agency.db"), limit=limit)  # type: ignore[arg-type]


def test_remediation_queue_rejects_receipt_tamper_on_owned_and_borrowed_reads(
    tmp_path: Path,
) -> None:
    store = _unknown_remediation_store(tmp_path)

    def tamper(_conn, detail, _row) -> None:
        detail["receipt"]["status"] = "approved"

    _mutate_remediation_event(store, tamper)
    with pytest.raises(RosterSyncError, match="receipt is invalid"):
        list_remediation_queue(store)

    conn = store._connect()
    try:
        conn.execute("BEGIN")
        with pytest.raises(RosterSyncError, match="receipt is invalid"):
            list_remediation_queue(store, _connection=conn)
        assert conn.in_transaction
        conn.rollback()
    finally:
        conn.close()


@pytest.mark.parametrize(
    "tamper_kind",
    ["missing_download", "source", "slug", "hash", "status", "candidate"],
)
def test_remediation_queue_checks_every_download_binding(
    tmp_path: Path,
    tamper_kind: str,
) -> None:
    store = _unknown_remediation_store(tmp_path / tamper_kind)

    def tamper(conn, detail, row) -> None:
        if tamper_kind == "missing_download":
            detail["download_id"] = "missing-download"
        elif tamper_kind == "source":
            detail["source_id"] = "wrong-source"
        elif tamper_kind == "slug":
            conn.execute(
                "UPDATE agent_import_events SET agent_slug = 'wrong-slug' WHERE id = ?",
                (row["id"],),
            )
        elif tamper_kind == "hash":
            conn.execute(
                "UPDATE agent_downloads SET hash = ? WHERE id = ?",
                ("f" * 64, detail["download_id"]),
            )
        elif tamper_kind == "status":
            conn.execute(
                "UPDATE agent_downloads SET status = 'candidate' WHERE id = ?",
                (detail["download_id"],),
            )
        else:
            conn.execute(
                "INSERT INTO agent_candidates "
                "(id, download_id, slug, status, quarantined_at) VALUES (?, ?, ?, ?, ?)",
                (
                    "forged-candidate",
                    detail["download_id"],
                    "unknown-encoding",
                    "pending",
                    "2026-07-18T00:00:00Z",
                ),
            )

    _mutate_remediation_event(store, tamper)
    expected = (
        "scan binding is invalid" if tamper_kind == "source" else "download binding is invalid"
    )
    with pytest.raises(RosterSyncError, match=expected):
        list_remediation_queue(store)


def test_manifest_outcome_remediation_attempt_contract_is_fail_closed(tmp_path: Path) -> None:
    candidate_agent = {"slug": "candidate-agent", "hash": "a" * 64}
    candidate = ingress_subject.ManifestImportOutcome(
        status="candidate",
        origin="source/candidate.md",
        relative_path="engineering/candidate.md",
        slug="candidate-agent",
        content_hash="a" * 64,
        finding="candidate_ready",
        remediation_attempt=subject.remediation_attempt("candidate", "candidate_ready"),
    )
    ignored = ingress_subject.ManifestImportOutcome(
        status="ignored",
        origin="source/README.md",
        relative_path="engineering/README.md",
        slug="",
        content_hash=_hash("notes"),
        finding="not_agent_definition:missing_front_matter",
        remediation_attempt=subject.remediation_attempt("notes", "ignored"),
    )
    quarantined_content = "unsafe\x07"
    finding = "unsafe_control:U+0007x1"
    attempt = subject.remediation_attempt(quarantined_content, finding)
    quarantined = ingress_subject.ManifestImportOutcome(
        status="quarantined",
        origin="source/unsafe.md",
        relative_path="engineering/unsafe.md",
        slug="unsafe-agent",
        content_hash=_hash(quarantined_content),
        finding=finding,
        content=quarantined_content,
        remediation_attempt=attempt,
    )
    validation = {
        "candidates_by_slug": {"candidate-agent": candidate_agent},
        "candidate_outcome_slugs": set(),
        "quarantined_entries": set(),
    }

    with pytest.raises(RosterSyncError, match="candidate outcome carries"):
        sync_subject._validate_manifest_outcome(candidate, **validation)
    with pytest.raises(RosterSyncError, match=r"ignored.*may not carry"):
        sync_subject._validate_manifest_outcome(ignored, **validation)
    with pytest.raises(RosterSyncError, match="carries remediation evidence"):
        sync_subject._validate_manifest_outcome(
            ingress_subject.ManifestImportOutcome(
                status=quarantined.status,
                origin=quarantined.origin,
                relative_path=quarantined.relative_path,
                slug=quarantined.slug,
                content_hash=quarantined.content_hash,
                finding=quarantined.finding,
                content=quarantined.content,
                source_content="unexpected source",
                remediation_attempt=attempt,
            ),
            **validation,
        )
    with pytest.raises(RosterSyncError, match="attempt is invalid"):
        sync_subject._validate_manifest_outcome(
            ingress_subject.ManifestImportOutcome(
                status="quarantined",
                origin=quarantined.origin,
                relative_path=quarantined.relative_path,
                slug=quarantined.slug,
                content_hash=quarantined.content_hash,
                finding=quarantined.finding,
                content=quarantined.content,
            ),
            **validation,
        )
    with pytest.raises(RosterSyncError, match="not source-bound"):
        sync_subject._validate_manifest_outcome(
            ingress_subject.ManifestImportOutcome(
                status="quarantined",
                origin=quarantined.origin,
                relative_path=quarantined.relative_path,
                slug=quarantined.slug,
                content_hash=quarantined.content_hash,
                finding="different finding",
                content=quarantined.content,
                remediation_attempt=attempt,
            ),
            **validation,
        )

    store = Store(tmp_path / "agency.db")
    conn = store._connect()
    try:
        with pytest.raises(RosterSyncError, match="queue receipt is invalid"):
            sync_subject._persist_rejected_manifest_entry(
                conn,
                store,
                "source-id",
                ingress_subject.ManifestImportOutcome(
                    status="quarantined",
                    origin=quarantined.origin,
                    relative_path=quarantined.relative_path,
                    slug=quarantined.slug,
                    content_hash=quarantined.content_hash,
                    finding=quarantined.finding,
                    content=quarantined.content,
                ),
                scan_id="scan-test",
                now="2026-07-18T00:00:00Z",
            )
    finally:
        conn.close()


def test_candidate_remediation_source_and_identity_checks_are_exact(
    monkeypatch: pytest.MonkeyPatch,
    known_profile,
) -> None:
    _repaired, deterministic = subject.remediate_source_text(known_profile.raw)
    assert deterministic is not None
    projected, receipt = semantic_projection.project_known_agent(
        {"slug": "fixture-agent", "name": "Fixture Agent", "division": "engineering"},
        deterministic,
        relative_path="engineering/fixture-agent.md",
    )
    projected.update(
        source="source",
        prompt_path="source/engineering/fixture-agent.md",
    )
    candidate = ingress_subject._normalize_agent(
        projected,
        _remediation_receipt_present=True,
    )
    base = ingress_subject.ManifestImportOutcome(
        status="candidate",
        origin=candidate["prompt_path"],
        relative_path="engineering/fixture-agent.md",
        slug="fixture-agent",
        content_hash=known_profile.raw_hash,
        finding="candidate_ready_after_remediation",
        source_content=known_profile.raw,
        remediation=receipt,
    )
    assert sync_subject._validate_candidate_remediation(base, candidate) == len(
        known_profile.raw.encode("utf-8")
    )

    with pytest.raises(RosterSyncError, match="unexpected source content"):
        sync_subject._validate_candidate_remediation(
            ingress_subject.ManifestImportOutcome(
                status="candidate",
                origin=base.origin,
                relative_path=base.relative_path,
                slug=base.slug,
                content_hash=base.content_hash,
                finding="candidate_ready",
                source_content=known_profile.raw,
            ),
            candidate,
        )
    with pytest.raises(RosterSyncError, match="missing original source"):
        sync_subject._validate_candidate_remediation(
            ingress_subject.ManifestImportOutcome(
                status=base.status,
                origin=base.origin,
                relative_path=base.relative_path,
                slug=base.slug,
                content_hash=base.content_hash,
                finding=base.finding,
                remediation=receipt,
            ),
            candidate,
        )
    with pytest.raises(RosterSyncError, match="source content hash"):
        sync_subject._validate_candidate_remediation(
            ingress_subject.ManifestImportOutcome(
                status=base.status,
                origin=base.origin,
                relative_path=base.relative_path,
                slug=base.slug,
                content_hash=base.content_hash,
                finding=base.finding,
                source_content=known_profile.raw + "changed",
                remediation=receipt,
            ),
            candidate,
        )

    monkeypatch.setattr(sync_subject, "verify_projected_remediation", lambda *_a, **_k: receipt)
    monkeypatch.setattr(sync_subject, "verify_projected_candidate_contract", lambda *_a, **_k: None)
    with pytest.raises(RosterSyncError, match="origin does not match"):
        sync_subject._validate_candidate_remediation(
            ingress_subject.ManifestImportOutcome(
                status=base.status,
                origin="wrong-origin",
                relative_path=base.relative_path,
                slug=base.slug,
                content_hash=base.content_hash,
                finding=base.finding,
                source_content=base.source_content,
                remediation=receipt,
            ),
            candidate,
        )
    with pytest.raises(RosterSyncError, match="identity does not match"):
        sync_subject._validate_candidate_remediation(
            base,
            {**candidate, "source_content_hash": "f" * 64},
        )


def test_remediated_source_persistence_requires_complete_evidence(
    tmp_path: Path,
    known_profile,
) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.raw)
    downloaded = download_from_source(str(source))
    [outcome] = downloaded.outcomes
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "remediation-evidence")

    conn = store._connect()
    try:
        with pytest.raises(RosterSyncError, match="missing its receipt"):
            sync_subject._persist_remediated_manifest_source(
                conn,
                store,
                source_id,
                ingress_subject.ManifestImportOutcome(
                    status=outcome.status,
                    origin=outcome.origin,
                    relative_path=outcome.relative_path,
                    slug=outcome.slug,
                    content_hash=outcome.content_hash,
                    finding=outcome.finding,
                    source_content=outcome.source_content,
                ),
                candidate_id="candidate",
                candidate_download_id="download",
                candidate_is_new=True,
                now="2026-07-18T00:00:00Z",
            )
    finally:
        conn.close()

    quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)
    conn = store._connect()
    try:
        conn.execute(
            "DELETE FROM agent_import_events WHERE event_type = 'manifest_entry_remediated'"
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RosterSyncError, match="evidence is incomplete or tampered"):
        quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)


@pytest.mark.parametrize(
    ("field", "tampered"),
    [
        ("slug", "wrong-agent"),
        ("name", "Wrong Agent"),
        ("display_name", "Wrong Agent"),
        ("division", "marketing"),
        ("description", "Tampered behavior."),
        ("authority", "approve"),
        ("context_mode", "direct_safe"),
        ("independence_group", "tampered-group"),
        ("expected_output_contract", "Return anything."),
        ("categories", ["tampered"]),
        ("capabilities", ["mutate production"]),
        ("anti_capabilities", []),
        ("task_types", ["implementation"]),
        ("preferred_when", ["always"]),
        ("avoid_when", []),
        ("required_tools", ["shell"]),
        ("tool_affinity", ["shell"]),
        ("supported_hosts", ["claude"]),
        ("supported_platforms", ["linux"]),
        ("conflicts_with", ["reviewer"]),
        ("requires", ["untrusted-agent"]),
        ("evidence_requirements", []),
        ("model_requirements", []),
        ("relative_path", "engineering/wrong-agent.md"),
        ("source_revision", "wrong-revision"),
        ("source_version", "wrong-revision"),
        ("source_content_hash", "0" * 64),
        ("content_hash", "0" * 64),
        ("audit_revision", "999"),
        ("audit_status", "unreviewed"),
        ("findings", []),
        ("prompt_path", "wrong-origin.md"),
    ],
)
def test_manifest_import_rejects_any_governed_contract_metadata_tamper(
    tmp_path: Path,
    known_profile,
    field: str,
    tampered: object,
) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.raw)
    downloaded = download_from_source(str(source))
    downloaded[0][field] = tampered
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "known-remediation")

    with pytest.raises(RosterSyncError):
        quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)
    conn = store._connect()
    try:
        assert conn.execute("SELECT COUNT(*) FROM agent_candidates").fetchone()[0] == 0
    finally:
        conn.close()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "Tampered Agent"),
        ("description", "Tampered behavior."),
        ("division", "marketing"),
        ("source_version", "wrong-revision"),
        ("categories", '["tampered"]'),
        ("capabilities", '["mutate production"]'),
        ("tool_affinity", '["shell"]'),
    ],
)
def test_review_rejects_persisted_projected_metadata_tamper(
    tmp_path: Path,
    known_profile,
    field: str,
    value: str,
) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.raw)
    downloaded = download_from_source(str(source))
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "known-remediation")
    candidate_ids, _outcomes = quarantine_manifest_import(
        downloaded,
        downloaded.outcomes,
        source_id,
        store,
    )
    conn = store._connect()
    try:
        conn.execute(
            f"UPDATE agent_candidates SET {field} = ? WHERE id = ?", (value, candidate_ids[0])
        )
        with pytest.raises(RosterSyncError, match="semantic projection"):
            audit_candidate_in_connection(conn, store, candidate_ids[0])
    finally:
        conn.close()


@pytest.mark.parametrize("field", ["authority", "capabilities"])
@pytest.mark.parametrize("stage", ["before_approval", "before_activation"])
def test_snapshot_tamper_never_restores_registered_contract_silently(
    tmp_path: Path,
    known_profile,
    field: str,
    stage: str,
) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.raw)
    downloaded = download_from_source(str(source))
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "known-remediation")
    candidate_ids, _outcomes = quarantine_manifest_import(
        downloaded,
        downloaded.outcomes,
        source_id,
        store,
    )
    snapshot = create_roster_diff(store, candidate_ids=candidate_ids)
    if stage == "before_activation":
        approve_snapshot(store, snapshot["snapshot_id"])

    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT manifest FROM agent_snapshots WHERE snapshot_id = ?",
            (snapshot["snapshot_id"],),
        ).fetchone()
        manifest = json.loads(row["manifest"])
        manifest["candidates"][0][field] = (
            "approve" if field == "authority" else ["mutate production"]
        )
        conn.execute(
            "UPDATE agent_snapshots SET manifest = ? WHERE snapshot_id = ?",
            (
                json.dumps(manifest, sort_keys=True, separators=(",", ":")),
                snapshot["snapshot_id"],
            ),
        )
        conn.commit()
    finally:
        conn.close()

    operation = approve_snapshot if stage == "before_approval" else activate_snapshot
    with pytest.raises(RosterSyncError, match="projected candidate contract"):
        operation(store, snapshot["snapshot_id"])
    assert store.get_active_roster() == []


def test_ingestion_rejects_tampered_remediation_event(tmp_path: Path, known_profile) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.raw)
    downloaded = download_from_source(str(source))
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "known-remediation")
    quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)

    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_import_events SET detail = '{}' "
            "WHERE event_type = 'manifest_entry_remediated'"
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RosterSyncError, match="remediation evidence"):
        quarantine_manifest_import(downloaded, downloaded.outcomes, source_id, store)


def test_remediated_source_replay_after_activation_reuses_raw_provenance(
    tmp_path: Path,
    known_profile,
) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.raw)
    downloaded = download_from_source(str(source))
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "known-remediation")
    first_ids, _outcomes = quarantine_manifest_import(
        downloaded,
        downloaded.outcomes,
        source_id,
        store,
    )
    snapshot = create_roster_diff(store, candidate_ids=first_ids)
    approve_snapshot(store, snapshot["snapshot_id"])
    activate_snapshot(store, snapshot["snapshot_id"])

    second_ids, _outcomes = quarantine_manifest_import(
        downloaded,
        downloaded.outcomes,
        source_id,
        store,
    )
    third_ids, _outcomes = quarantine_manifest_import(
        downloaded,
        downloaded.outcomes,
        source_id,
        store,
    )

    assert second_ids != first_ids
    assert third_ids == second_ids
    conn = store._connect()
    try:
        raw_count = conn.execute(
            "SELECT COUNT(*) FROM agent_downloads WHERE hash = ?",
            (known_profile.raw_hash,),
        ).fetchone()[0]
        event_count = conn.execute(
            "SELECT COUNT(*) FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediated'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert raw_count == 1
    assert event_count == 2


def test_review_recomputes_semantic_projection_path(tmp_path: Path, known_profile) -> None:
    source = tmp_path / "source"
    _write_known_manifest(source, known_profile.raw)
    downloaded = download_from_source(str(source))
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "known-remediation")
    candidate_ids, _outcomes = quarantine_manifest_import(
        downloaded,
        downloaded.outcomes,
        source_id,
        store,
    )

    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT id, detail FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediated'"
        ).fetchone()
        detail = json.loads(row["detail"])
        detail["relative_path"] = "engineering/wrong-agent.md"
        conn.execute(
            "UPDATE agent_import_events SET detail = ? WHERE id = ?",
            (json.dumps(detail, sort_keys=True, separators=(",", ":")), row["id"]),
        )
        with pytest.raises(RosterSyncError, match="semantic projection"):
            audit_candidate_in_connection(conn, store, candidate_ids[0])
    finally:
        conn.close()
