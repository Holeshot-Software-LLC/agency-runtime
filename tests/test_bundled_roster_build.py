"""Deterministic and filesystem-safe bundled-roster generation tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import build_bundled_roster as subject


def _contract(relative_path: str, slug: str) -> dict[str, object]:
    values: dict[str, object] = {
        "relative_path": relative_path,
        "slug": slug,
        "display_name": slug.replace("-", " ").title(),
        "division": "engineering",
        "description": "A bounded engineering specialist.",
        "authority": "modify",
        "context_mode": "isolated_only",
        "independence_group": "implementation",
        "expected_output_contract": "Return a verified implementation.",
        "source_revision": "a" * 40,
        "content_hash": "b" * 64,
        "audit_revision": "1",
        "audit_status": "approved",
        **{field: [] for field in subject.CONTRACT_LIST_FIELDS},
    }
    values.update(
        categories=["engineering"],
        capabilities=["Implement bounded changes."],
        anti_capabilities=["Do not claim unverified completion."],
        task_types=["Implementation"],
        preferred_when=["A focused implementation is requested."],
        avoid_when=["The task is outside engineering."],
        required_tools=["repository"],
        supported_hosts=["codex"],
        supported_platforms=["windows"],
        evidence_requirements=["Provide test evidence."],
        model_requirements=["code-reasoning"],
        findings=["No unsafe authority was retained."],
    )
    return {field: values[field] for field in subject.CONTRACT_FIELDS}


def _write_test_audit(tmp_path: Path, contracts: list[dict[str, object]]) -> dict[str, Any]:
    artifact = tmp_path / "batch-test.json"
    artifact_bytes = (json.dumps(contracts, indent=2) + "\n").encode()
    artifact.write_bytes(artifact_bytes)
    review = tmp_path / "batch-test-review.md"
    review_bytes = b"---\ntitle: Test audit\n---\n\n# Test audit\n"
    review.write_bytes(review_bytes)
    return {
        "audit_revision": "1",
        "source": {"revision": "a" * 40},
        "sources": {"agency-agents": {"revision": "a" * 40, "inventory": "divisions"}},
        "expected": {
            "total_agents": len(contracts),
            "status_counts": {"approved": len(contracts)},
            "division_counts": {"engineering": len(contracts)},
            "batches": {
                "batch-test.json": {
                    "count": len(contracts),
                    "division_counts": {"engineering": len(contracts)},
                    "review": review.name,
                    "artifact_sha256": hashlib.sha256(artifact_bytes).hexdigest(),
                    "review_sha256": hashlib.sha256(review_bytes).hexdigest(),
                }
            },
        },
        "enums": {
            "authority": ["advise", "approve", "modify", "plan", "review"],
            "context_mode": ["direct_safe", "isolated_only"],
            "audit_status": ["approved", "quarantined", "retired"],
            "supported_hosts": ["claude", "codex", "hermes", "openclaw"],
            "supported_platforms": ["linux", "windows"],
        },
        "nonempty_list_fields": [
            field
            for field in subject.CONTRACT_LIST_FIELDS
            if field
            not in {
                "required_tools",
                "supported_hosts",
                "supported_platforms",
                "conflicts_with",
                "requires",
            }
        ],
        "quarantines": {},
        "remediations": {},
    }


def test_write_bundle_is_idempotent_atomic_and_removes_stale_files(tmp_path: Path) -> None:
    output = tmp_path / "data"
    subject._write_bundle(
        output,
        {
            "manifest.json": b"first",
            "prompts/alpha.txt": b"alpha",
        },
    )
    subject._write_bundle(output, {"manifest.json": b"second"})

    assert (output / "manifest.json").read_bytes() == b"second"
    assert not (output / "prompts" / "alpha.txt").exists()
    assert subject._actual_files(output) == {"manifest.json"}
    assert not list(output.rglob("*.tmp"))


def test_check_bundle_reports_missing_stale_and_unexpected_in_order(tmp_path: Path) -> None:
    output = tmp_path / "data"
    output.mkdir()
    (output / "stale.txt").write_bytes(b"old")
    (output / "unexpected.txt").write_bytes(b"unexpected")

    assert subject._check_bundle(
        output,
        {
            "missing.txt": b"missing",
            "stale.txt": b"new",
        },
    ) == [
        "missing generated file: missing.txt",
        "stale generated file: stale.txt",
        "unexpected generated file: unexpected.txt",
    ]


def test_write_bundle_rejects_non_directory_output(tmp_path: Path) -> None:
    output = tmp_path / "data"
    output.write_text("not a directory", encoding="utf-8")

    with pytest.raises(subject.BundleBuildError, match="output must be a directory"):
        subject._write_bundle(output, {"manifest.json": b"value"})


def test_write_bundle_rejects_symlinked_output_file(tmp_path: Path) -> None:
    output = tmp_path / "data"
    output.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = output / "manifest.json"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(subject.BundleBuildError, match="contains a symlink"):
        subject._write_bundle(output, {"manifest.json": b"replacement"})
    assert outside.read_text(encoding="utf-8") == "outside"


def test_generation_publish_failure_restores_previous_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "data"
    subject._write_bundle(
        output,
        {
            "manifest.json": b"old-manifest",
            "prompts/old.txt": b"old-prompt",
        },
    )
    original_replace = subject.os.replace

    def fail_new_generation(source: object, destination: object) -> None:
        source_path = Path(source)  # type: ignore[arg-type]
        destination_path = Path(destination)  # type: ignore[arg-type]
        if source_path.name.startswith(".data.staging-") and destination_path == output:
            raise OSError("simulated generation publication failure")
        original_replace(source, destination)

    monkeypatch.setattr(subject.os, "replace", fail_new_generation)
    with pytest.raises(subject.BundleBuildError, match="rolled back"):
        subject._write_bundle(
            output,
            {
                "manifest.json": b"new-manifest",
                "prompts/new.txt": b"new-prompt",
            },
        )

    assert (output / "manifest.json").read_bytes() == b"old-manifest"
    assert (output / "prompts" / "old.txt").read_bytes() == b"old-prompt"
    assert not (output / "prompts" / "new.txt").exists()
    assert not list(tmp_path.glob(".data.staging-*"))
    assert not list(tmp_path.glob(".data.backup-*"))


def test_staging_failure_never_mutates_previous_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "data"
    subject._write_bundle(output, {"manifest.json": b"old"})

    def fail_staging(staging: Path, _files: object) -> None:
        (staging / "partial.txt").write_bytes(b"partial")
        raise subject.BundleBuildError("simulated staging failure")

    monkeypatch.setattr(subject, "_write_staged_bundle", fail_staging)
    with pytest.raises(subject.BundleBuildError, match="staging failure"):
        subject._write_bundle(output, {"manifest.json": b"new"})

    assert (output / "manifest.json").read_bytes() == b"old"
    assert not list(tmp_path.glob(".data.staging-*"))


@pytest.mark.parametrize(
    "relative_path",
    [
        "../escape.txt",
        r"prompts\escape.txt",
        "C:/escape.txt",
        "prompts/trailing. ",
        "prompts/CON.txt",
    ],
)
def test_write_bundle_rejects_unsafe_generated_paths(
    tmp_path: Path,
    relative_path: str,
) -> None:
    output = tmp_path / "data"

    with pytest.raises(subject.BundleBuildError, match="output path is unsafe"):
        subject._write_bundle(output, {relative_path: b"unsafe"})
    assert not (tmp_path / "escape.txt").exists()


def test_check_bundle_bounds_an_oversized_generated_file(tmp_path: Path) -> None:
    output = tmp_path / "data"
    output.mkdir()
    (output / "manifest.json").write_bytes(b"oversized")

    assert subject._check_bundle(output, {"manifest.json": b"x"}) == [
        "stale generated file: manifest.json"
    ]


def test_upstream_license_uses_git_blob_and_canonical_lf_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "LICENSE").write_bytes(b"working tree\r\nbytes\r\n")
    calls: list[tuple[tuple[str, ...], str]] = []

    def fake_git(
        source: Path,
        arguments: tuple[str, ...],
        *,
        label: str,
    ) -> bytes:
        assert source == tmp_path
        calls.append((arguments, label))
        return b"tracked blob\r\nwith mixed\rline endings\n"

    monkeypatch.setattr(subject, "_run_git", fake_git)

    assert subject._canonical_upstream_license(tmp_path, "a" * 40) == (
        b"tracked blob\nwith mixed\nline endings\n"
    )
    assert calls == [(("cat-file", "blob", f"{'a' * 40}:LICENSE"), "license blob")]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"\xff", "not UTF-8"),
        (b"license\x00text", "NUL byte"),
        (b"", "empty or exceeds"),
    ],
)
def test_license_canonicalization_rejects_invalid_text(
    payload: bytes,
    message: str,
) -> None:
    with pytest.raises(subject.BundleBuildError, match=message):
        subject._canonical_lf_text_bytes(payload, label="license")


def test_actual_files_rejects_windows_reparse_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "data"
    reparse = output / "junction"
    reparse.mkdir(parents=True)
    original = subject._metadata_is_link_or_reparse
    inspections = 0

    def simulated_reparse(metadata: Any) -> bool:
        nonlocal inspections
        inspections += 1
        return original(metadata) or inspections > 1

    monkeypatch.setattr(subject, "_metadata_is_link_or_reparse", simulated_reparse)
    with pytest.raises(subject.BundleBuildError, match="reparse point"):
        subject._actual_files(output)


def test_bounded_reader_rejects_hardlinked_input(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    alias = tmp_path / "alias.json"
    source.write_bytes(b"{}")
    try:
        subject.os.link(source, alias)
    except OSError as exc:
        pytest.skip(f"hardlink creation is unavailable: {exc}")

    with pytest.raises(subject.BundleBuildError, match="exactly one hard link"):
        subject._read_regular_bytes(source, maximum_bytes=16, label="test artifact")


def test_load_audits_enforces_complete_batch_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contracts = [
        _contract("engineering/alpha.md", "alpha"),
        _contract("engineering/beta.md", "beta"),
    ]
    manifest = _write_test_audit(tmp_path, contracts)
    monkeypatch.setattr(subject, "MAX_BUNDLED_AGENTS", 1)

    with pytest.raises(subject.BundleBuildError, match="1-agent package limit"):
        subject._load_audits(tmp_path, manifest)


def test_source_inventory_rejects_duplicate_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = tmp_path / "engineering" / "alpha.md"
    prompt.parent.mkdir()
    prompt.write_text("prompt", encoding="utf-8")

    class Downloaded(list[dict[str, Any]]):
        def __init__(self, values: list[dict[str, Any]]) -> None:
            super().__init__(values)
            self.outcomes: list[Any] = []

    candidate = {"prompt_path": str(prompt)}
    monkeypatch.setattr(
        subject, "download_from_source", lambda _source: Downloaded([candidate] * 2)
    )

    with pytest.raises(subject.BundleBuildError, match="duplicate candidate"):
        subject._source_inventory(tmp_path)


def test_manifest_entry_rejects_oversized_governed_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = _contract("engineering/alpha.md", "alpha")
    monkeypatch.setattr(subject, "MAX_PROMPT_BYTES", 1)

    with pytest.raises(subject.BundleBuildError, match="governed prompt exceeds package limit"):
        subject._manifest_entry(contract)


def test_tracked_audit_is_complete_exact_and_reproducible() -> None:
    audit_dir = subject.DEFAULT_AUDIT_DIR.resolve(strict=True)
    manifest = subject._load_audit_manifest(audit_dir)
    contracts = subject._load_audits(audit_dir, manifest)

    # The division manifest is pinned by its immutable Git blob hash; the
    # earlier pin was the CRLF hash of a Windows checkout and could not be
    # rebuilt from an LF checkout (found while adding the second source, AR-364).
    assert manifest["source"] == {
        "repository": "https://github.com/msitarzewski/agency-agents",
        "origin": "https://github.com/msitarzewski/agency-agents.git",
        "revision": "459dce837db3bdfdc4763d3fefd1fd854e73c8f1",
        "division_manifest": "divisions.json",
        "division_manifest_sha256": "15136bcf43ff95dd2ef827519c96cfee3fa3ebe35057d69ff1cd49a1a9e48add",
    }
    assert set(manifest["sources"]) == {"agency-agents", "ecc"}
    assert manifest["sources"]["agency-agents"]["inventory"] == "divisions"
    assert manifest["sources"]["ecc"] == {
        "id": "ecc",
        "repository": "https://github.com/affaan-m/ECC",
        "origin": "https://github.com/affaan-m/ECC.git",
        "revision": "ca185ef5f7667078a1e70a763bd3a9c71c48acf0",
        "license": "MIT",
        "inventory": "explicit",
    }
    assert manifest["expected"]["total_agents"] == len(contracts) == 265
    assert len(manifest["expected"]["division_counts"]) == 17
    assert manifest["expected"]["status_counts"] == {"approved": 265}
    assert {path for path, item in contracts.items() if item["source"] == "ecc"} == {
        "agents/silent-failure-hunter.md",
        "agents/type-design-analyzer.md",
    }
    assert set(manifest["remediations"]) == {
        "engineering/engineering-mobile-app-builder.md",
        "marketing/marketing-app-store-optimizer.md",
    }
    assert set(manifest["expected"]["batches"]) == {
        "batch-a.json",
        "batch-ecc-review.json",
        "batch-engineering.json",
        "batch-marketing-security.json",
        "batch-specialized.json",
    }
    assert (
        sum(descriptor["count"] for descriptor in manifest["expected"]["batches"].values()) == 265
    )
    for review in audit_dir.glob("batch-*-review.md"):
        text = review.read_text(encoding="utf-8")
        assert "297" not in text
        assert "19 divisions" not in text
        assert "build/roster-audit" not in text


def test_manifest_rejects_extra_fields_nonofficial_origin_and_nonexecution_host(
    tmp_path: Path,
) -> None:
    canonical = json.loads(
        (subject.DEFAULT_AUDIT_DIR / subject.AUDIT_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    cases: list[tuple[dict[str, Any], str]] = []

    extra = json.loads(json.dumps(canonical))
    extra["unexpected"] = True
    cases.append((extra, "fields must match"))

    origin = json.loads(json.dumps(canonical))
    origin["source"]["origin"] = "https://example.invalid/agents.git"
    cases.append((origin, "official agency-agents origin"))

    host = json.loads(json.dumps(canonical))
    host["enums"]["supported_hosts"].append("litellm")
    cases.append((host, "supported_hosts enum"))

    for raw, match in cases:
        (tmp_path / subject.AUDIT_MANIFEST_NAME).write_text(
            json.dumps(raw, indent=2) + "\n",
            encoding="utf-8",
        )
        with pytest.raises(subject.BundleBuildError, match=match):
            subject._load_audit_manifest(tmp_path)


def test_audit_file_set_and_review_hash_are_exact(tmp_path: Path) -> None:
    contract = _contract("engineering/alpha.md", "alpha")
    manifest = _write_test_audit(tmp_path, [contract])
    extra = tmp_path / "batch-extra.json"
    extra.write_text("[]\n", encoding="utf-8")
    with pytest.raises(subject.BundleBuildError, match=r"extra=.*batch-extra"):
        subject._load_audits(tmp_path, manifest)

    extra.unlink()
    (tmp_path / "batch-test-review.md").write_text("changed\n", encoding="utf-8")
    with pytest.raises(subject.BundleBuildError, match="review hash"):
        subject._load_audits(tmp_path, manifest)


def test_audit_hashes_canonicalize_lf_while_source_hashes_remain_raw(
    tmp_path: Path,
) -> None:
    contract = _contract("engineering/alpha.md", "alpha")
    manifest = _write_test_audit(tmp_path, [contract])
    artifact = tmp_path / "batch-test.json"
    review = tmp_path / "batch-test-review.md"
    artifact_lf = artifact.read_bytes()
    review_lf = review.read_bytes()
    artifact_crlf = artifact_lf.replace(b"\n", b"\r\n")
    review_crlf = review_lf.replace(b"\n", b"\r\n")
    artifact.write_bytes(artifact_crlf)
    review.write_bytes(review_crlf)

    assert subject._load_audits(tmp_path, manifest) == {
        "engineering/alpha.md": {**contract, "source": subject.SOURCE_ID}
    }
    assert subject._sha256(artifact_lf) != subject._sha256(artifact_crlf)
    assert subject._sha256(review_lf) != subject._sha256(review_crlf)


def test_source_definition_validation_preserves_raw_lf_and_crlf_identity(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    relative_path = "engineering/alpha.md"
    definition = source / "engineering" / "alpha.md"
    definition.parent.mkdir(parents=True)
    lf_source = (
        b"---\n"
        b"name: Alpha\n"
        b"description: Exact source identity fixture.\n"
        b"---\n"
        b"# Alpha\n"
        b"Perform bounded work.\n"
    )
    crlf_source = lf_source.replace(b"\n", b"\r\n")
    lf_hash = subject._sha256(lf_source)
    crlf_hash = subject._sha256(crlf_source)
    assert lf_hash != crlf_hash

    contract = _contract(relative_path, "alpha")
    contract["content_hash"] = lf_hash
    candidate = {
        "name": contract["display_name"],
        "division": contract["division"],
        "slug": contract["slug"],
    }
    outcome = SimpleNamespace(slug="alpha", status="candidate")
    audit = {"remediations": {}, "quarantines": {}}

    definition.write_bytes(lf_source)
    assert subject._read_source_definition(source, relative_path) == lf_source
    subject._validate_source_entry(
        source,
        "a" * 40,
        audit,
        relative_path,
        contract,
        candidate,
        outcome,
    )

    definition.write_bytes(crlf_source)
    assert subject._read_source_definition(source, relative_path) == crlf_source
    with pytest.raises(subject.BundleBuildError, match="source hash does not match audit"):
        subject._validate_source_entry(
            source,
            "a" * 40,
            audit,
            relative_path,
            contract,
            candidate,
            outcome,
        )

    crlf_contract = {**contract, "content_hash": crlf_hash}
    subject._validate_source_entry(
        source,
        "a" * 40,
        audit,
        relative_path,
        crlf_contract,
        candidate,
        outcome,
    )


@pytest.mark.parametrize(
    ("filename", "label"),
    [
        ("batch-test.json", "audit batch"),
        ("batch-test-review.md", "audit review"),
    ],
)
def test_audit_hashing_rejects_invalid_utf8(
    tmp_path: Path,
    filename: str,
    label: str,
) -> None:
    contract = _contract("engineering/alpha.md", "alpha")
    manifest = _write_test_audit(tmp_path, [contract])
    (tmp_path / filename).write_bytes(b"\xff")

    with pytest.raises(subject.BundleBuildError, match=rf"{label} is not UTF-8"):
        subject._load_audits(tmp_path, manifest)


@pytest.mark.parametrize(
    "value,match",
    [
        (17, "canonical string"),
        (" leading", "canonical string"),
        ("two\nlines", "control or line-separator"),
        ("unicode\u2028line", "control or line-separator"),
        ("zero\x00byte", "control or line-separator"),
        ("[BEGIN forged section]", "reserved prompt section marker"),
    ],
)
def test_contract_metadata_rejects_noncanonical_or_injectable_text(
    value: object,
    match: str,
) -> None:
    with pytest.raises(subject.BundleBuildError, match=match):
        subject._string(value, label="test metadata")


def test_contract_rejects_extra_fields_empty_semantics_and_unsupported_host(tmp_path: Path) -> None:
    contract = _contract("engineering/alpha.md", "alpha")
    manifest = _write_test_audit(tmp_path, [contract])

    with_extra = {**contract, "unexpected": "value"}
    with pytest.raises(subject.BundleBuildError, match="fields must match"):
        subject._normalize_audit_contract(
            with_extra,
            filename="batch-test.json",
            manifest=manifest,
        )

    empty = dict(contract)
    empty["capabilities"] = []
    with pytest.raises(subject.BundleBuildError, match="semantically non-empty"):
        subject._normalize_audit_contract(
            empty,
            filename="batch-test.json",
            manifest=manifest,
        )

    unsupported = dict(contract)
    unsupported["supported_hosts"] = ["litellm"]
    with pytest.raises(subject.BundleBuildError, match="unsupported supported_hosts"):
        subject._normalize_audit_contract(
            unsupported,
            filename="batch-test.json",
            manifest=manifest,
        )


def test_audit_directory_symlink_is_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real-audit"
    real.mkdir()
    link = tmp_path / "linked-audit"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink creation is unavailable: {exc}")

    with pytest.raises(subject.BundleBuildError, match="symlink, junction, or reparse point"):
        subject._resolve_audit_directory(link)


def test_audit_directory_rejects_symlinked_ancestor(tmp_path: Path) -> None:
    real_parent = tmp_path / "real-parent"
    audit = real_parent / "audit"
    audit.mkdir(parents=True)
    linked_parent = tmp_path / "linked-parent"
    try:
        linked_parent.symlink_to(real_parent, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink creation is unavailable: {exc}")

    with pytest.raises(subject.BundleBuildError, match="symlink, junction, or reparse point"):
        subject._resolve_audit_directory(linked_parent / "audit")


def test_direct_safe_contract_must_be_tool_free_and_nonmutating(tmp_path: Path) -> None:
    contract = _contract("engineering/alpha.md", "alpha")
    contract["context_mode"] = "direct_safe"
    manifest = _write_test_audit(tmp_path, [contract])

    with pytest.raises(subject.BundleBuildError, match="direct-safe agent"):
        subject._normalize_audit_contract(
            contract,
            filename="batch-test.json",
            manifest=manifest,
        )


@pytest.mark.parametrize("failure", ["revision", "origin", "dirty"])
def test_source_checkout_requires_exact_pinned_clean_official_git_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    manifest = subject._load_audit_manifest(subject.DEFAULT_AUDIT_DIR.resolve(strict=True))

    def fake_git(_source: Path, arguments: tuple[str, ...], *, label: str) -> bytes:
        del label
        if arguments[0] == "rev-parse":
            revision = "b" * 40 if failure == "revision" else manifest["source"]["revision"]
            return f"{revision}\n".encode()
        if arguments[0] == "config":
            origin = (
                "https://example.invalid/roster.git"
                if failure == "origin"
                else subject.OFFICIAL_SOURCE_ORIGIN
            )
            return f"{origin}\n".encode()
        return b" M engineering/agent.md\n" if failure == "dirty" else b""

    monkeypatch.setattr(subject, "_run_git", fake_git)
    expected = {
        "revision": "revision does not match",
        "origin": "origin does not match",
        "dirty": "must be clean",
    }[failure]
    with pytest.raises(subject.BundleBuildError, match=expected):
        subject._validate_source_checkout(tmp_path, manifest)


@pytest.mark.parametrize(
    "field,actual,match",
    [
        ("name", "Wrong Name", "display name"),
        ("division", "marketing", "division"),
        ("slug", "wrong-slug", "identity slug"),
    ],
)
def test_source_identity_must_match_audited_display_division_and_slug(
    field: str,
    actual: str,
    match: str,
) -> None:
    contract = _contract("engineering/alpha.md", "alpha")
    candidate = {
        "name": contract["display_name"],
        "division": contract["division"],
        "slug": contract["slug"],
    }
    candidate[field] = actual
    with pytest.raises(subject.BundleBuildError, match=match):
        subject._validate_source_identity(
            b"unused",
            relative_path=str(contract["relative_path"]),
            contract=contract,
            candidate=candidate,
        )


def test_quarantine_controls_are_byte_exact_and_bound_to_ingress_finding() -> None:
    raw = b"ab\x04cd\x04"
    controls = subject._unsafe_source_controls(raw, relative_path="engineering/unsafe.md")
    assert controls == [
        {
            "codepoint": "U+0004",
            "count": 2,
            "byte_offsets": [2, 5],
            "offsets_truncated": False,
        }
    ]
    assert subject._unsafe_source_controls(
        "é\x80".encode(),
        relative_path="engineering/c1.md",
    ) == [
        {
            "codepoint": "U+0080",
            "count": 1,
            "byte_offsets": [2],
            "offsets_truncated": False,
        }
    ]
    expected = {
        "unsafe_controls": controls,
        "ingress_finding": "unsafe_control:U+0004x2@2|5",
    }
    contract = _contract("engineering/unsafe.md", "unsafe")
    contract["audit_status"] = "quarantined"
    subject._validate_quarantine_evidence(
        raw,
        relative_path="engineering/unsafe.md",
        contract=contract,
        outcome=SimpleNamespace(
            status="quarantined",
            finding="unsafe_control:U+0004x2@2|5",
        ),
        expected=expected,
    )

    expected["unsafe_controls"] = [{"codepoint": "U+0004", "byte_offsets": [2, 4]}]
    with pytest.raises(subject.BundleBuildError, match="byte evidence"):
        subject._validate_quarantine_evidence(
            raw,
            relative_path="engineering/unsafe.md",
            contract=contract,
            outcome=SimpleNamespace(status="quarantined", finding="unsafe_control:U+0004x2"),
            expected=expected,
        )


def test_quarantine_supports_zero_control_mojibake_evidence() -> None:
    relative_path = "engineering/mojibake.md"
    raw = "---\nname: Mojibake\n---\n## ðŸš€ Broken\n".encode()
    expected = {
        "unsafe_controls": [],
        "ingress_finding": subject.SUSPICIOUS_ENCODING_FINDING,
    }
    contract = _contract(relative_path, "mojibake")
    contract["audit_status"] = "quarantined"
    outcome = SimpleNamespace(
        status="quarantined",
        finding=subject.SUSPICIOUS_ENCODING_FINDING,
    )

    subject._validate_quarantine_evidence(
        raw,
        relative_path=relative_path,
        contract=contract,
        outcome=outcome,
        expected=expected,
    )
    with pytest.raises(subject.BundleBuildError, match="suspicious-encoding evidence"):
        subject._validate_quarantine_evidence(
            b"---\nname: Safe\n---\n## Safe\n",
            relative_path=relative_path,
            contract=contract,
            outcome=outcome,
            expected=expected,
        )

    [normalized] = subject._normalize_manifest_quarantines(
        [
            {
                "relative_path": relative_path,
                "findings": ["source_encoding_corruption"],
                "unsafe_controls": [],
                "ingress_finding": subject.SUSPICIOUS_ENCODING_FINDING,
            }
        ]
    ).values()
    assert normalized["unsafe_controls"] == []


def test_governed_prompt_uses_audited_brief_without_raw_upstream_body() -> None:
    contract = _contract("engineering/alpha.md", "alpha")
    prompt = subject._governed_prompt(contract)

    assert "A bounded engineering specialist." in prompt
    assert "Source SHA-256:" in prompt
    assert "quoted upstream" not in prompt.casefold()
    assert "BEGIN QUOTED" not in prompt
