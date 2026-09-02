"""Focused fail-closed branch coverage for the packaged roster boundary."""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.roster import bundled as subject


@pytest.fixture(autouse=True)
def _clear_bundled_caches() -> Iterator[None]:
    subject.clear_bundled_roster_cache()
    yield
    subject.clear_bundled_roster_cache()


def _approved_agent() -> tuple[dict[str, Any], dict[str, str]]:
    manifest = subject.bundled_manifest()
    entry = next(
        item
        for item in manifest["agents"]
        if item["audit_status"] == "approved" and "remediation" not in item
    )
    return copy.deepcopy(entry), copy.deepcopy(manifest["source"])


def _raw_source() -> dict[str, str]:
    """The primary source block as packaged (the validated copy also carries ``id``)."""

    source = copy.deepcopy(subject.bundled_manifest()["source"])
    source.pop("id", None)
    return source


def _remediated_agent() -> tuple[dict[str, Any], dict[str, Any]]:
    entry = next(item for item in subject.bundled_manifest()["agents"] if "remediation" in item)
    return copy.deepcopy(entry), copy.deepcopy(entry)


def _install_manifest_payload(
    monkeypatch: pytest.MonkeyPatch,
    manifest: object,
) -> None:
    payload = b"manifest"
    digest = hashlib.sha256(payload).hexdigest().encode()

    def resource(relative_path: str, *, limit: int, label: str) -> bytes:
        del limit, label
        return digest if relative_path == subject._MANIFEST_DIGEST_FILE else payload

    monkeypatch.setattr(subject, "_resource", resource)
    monkeypatch.setattr(subject, "safe_load_bounded_json", lambda *_args, **_kwargs: manifest)
    monkeypatch.setattr(
        subject,
        "_validate_sources",
        lambda _manifest: {
            subject.PRIMARY_SOURCE_ID: {
                "id": subject.PRIMARY_SOURCE_ID,
                "repository": subject.SOURCE_REPOSITORY,
                "revision": "a" * 40,
                "license": subject.SOURCE_LICENSE,
                "license_file": subject.SOURCE_LICENSE_FILE,
                "license_hash": "b" * 64,
            }
        },
    )


def test_package_boundary_rejects_non_text_paths_missing_resources_and_bad_utf8(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(subject.BundledRosterError, match="safe package-relative path"):
        subject._safe_relative_path(1, label="resource")

    class MissingNode:
        def joinpath(self, _part: str) -> MissingNode:
            return self

        def open(self, _mode: str) -> None:
            raise OSError("unavailable")

    monkeypatch.setattr(subject.resources, "files", lambda _package: MissingNode())
    with pytest.raises(subject.BundledRosterError, match="resource is unavailable"):
        subject._resource("manifest.json", limit=128, label="resource")

    with pytest.raises(subject.BundledRosterError, match="not valid UTF-8"):
        subject._decode_utf8(b"\xff", label="resource")


def test_package_list_and_source_provenance_reject_untrusted_values() -> None:
    with pytest.raises(subject.BundledRosterError, match="contains duplicates"):
        subject._string_list({"capabilities": ["review", "review"]}, "capabilities")

    source = _raw_source()
    source["revision"] = "not-a-revision"
    with pytest.raises(subject.BundledRosterError, match="source revision is invalid"):
        subject._validate_source(source)

    source = _raw_source()
    source["license_hash"] = "not-a-hash"
    with pytest.raises(subject.BundledRosterError, match="license hash is invalid"):
        subject._validate_source(source)

    source = _raw_source()
    source["license_hash"] = "f" * 64
    with pytest.raises(subject.BundledRosterError, match="license hash does not match"):
        subject._validate_source(source)


def test_remediation_rejects_inactive_unknown_and_contract_mismatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry, result = _remediated_agent()
    result["audit_status"] = "quarantined"
    with pytest.raises(subject.BundledRosterError, match=r"inactive.*remediation"):
        subject._validate_remediation(entry, result)

    entry, result = _remediated_agent()
    contract = subject.contract_for_source_hash(result["source_content_hash"])
    assert contract is not None

    with monkeypatch.context() as scoped:
        scoped.setattr(subject, "contract_for_source_hash", lambda _source_hash: None)
        with pytest.raises(subject.BundledRosterError, match="source profile is unknown"):
            subject._validate_remediation(entry, result)

    monkeypatch.setattr(subject, "contract_for_source_hash", lambda _source_hash: contract)
    result["description"] = "tampered"
    with pytest.raises(subject.BundledRosterError, match="does not match its registry"):
        subject._validate_remediation(entry, result)

    entry, result = _remediated_agent()
    result["prompt_hash"] = "f" * 64
    with pytest.raises(subject.BundledRosterError, match="prompt does not match"):
        subject._validate_remediation(entry, result)


def test_remediation_rejects_invalid_receipts_and_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry, result = _remediated_agent()

    def fail_verification(*_args: object, **_kwargs: object) -> None:
        raise subject.RosterRemediationError("invalid")

    monkeypatch.setattr(subject, "verify_packaged_remediation", fail_verification)
    with pytest.raises(subject.BundledRosterError, match="receipt is invalid"):
        subject._validate_remediation(entry, result)

    entry, result = _remediated_agent()
    receipt = SimpleNamespace(findings_original=("tampered",))
    monkeypatch.setattr(
        subject,
        "verify_packaged_remediation",
        lambda *_args, **_kwargs: receipt,
    )
    with pytest.raises(subject.BundledRosterError, match="findings do not match"):
        subject._validate_remediation(entry, result)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("slug", "A", "slug is invalid"),
        ("source_revision", "c" * 40, "source revision does not match"),
        ("source_content_hash", "not-a-hash", "source content hash is invalid"),
        ("audit_status", "unknown", "audit status is invalid"),
        ("version", "not-a-version", "immutable version is invalid"),
        ("prompt_hash", None, "prompt hash is invalid"),
        ("prompt_file", "prompts/wrong.txt", "prompt path is not canonical"),
    ],
)
def test_agent_validation_rejects_invalid_identity_and_prompt_contracts(
    field: str,
    value: object,
    message: str,
) -> None:
    entry, source = _approved_agent()
    entry[field] = value

    with pytest.raises(subject.BundledRosterError, match=message):
        subject._validate_agent(entry, sources={subject.PRIMARY_SOURCE_ID: source})


def test_agent_validation_rejects_inactive_prompt_and_version_mismatch() -> None:
    entry, source = _approved_agent()
    entry["audit_status"] = "quarantined"
    with pytest.raises(subject.BundledRosterError, match=r"inactive.*prompt"):
        subject._validate_agent(entry, sources={subject.PRIMARY_SOURCE_ID: source})

    entry, source = _approved_agent()
    entry["audit_status"] = "quarantined"
    entry["prompt_file"] = None
    entry["prompt_hash"] = None
    entry["version"] = "sha256:" + "f" * 64
    entry.pop("remediation", None)
    with pytest.raises(subject.BundledRosterError, match="immutable version does not match"):
        subject._validate_agent(entry, sources={subject.PRIMARY_SOURCE_ID: source})


def test_relationship_validation_rejects_missing_dependencies() -> None:
    with pytest.raises(subject.BundledRosterError, match="relationship is invalid"):
        subject._validate_relationships(
            [
                {
                    "slug": "reviewer",
                    "audit_status": "approved",
                    "conflicts_with": [],
                    "requires": ["missing"],
                }
            ]
        )


def test_manifest_rejects_invalid_json_and_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"invalid"
    digest = hashlib.sha256(payload).hexdigest().encode()

    def resource(relative_path: str, *, limit: int, label: str) -> bytes:
        del limit, label
        return digest if relative_path == subject._MANIFEST_DIGEST_FILE else payload

    monkeypatch.setattr(subject, "_resource", resource)
    monkeypatch.setattr(
        subject,
        "safe_load_bounded_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid")),
    )
    with pytest.raises(subject.BundledRosterError, match="invalid JSON"):
        subject._validated_manifest()

    subject._validated_manifest.cache_clear()
    _install_manifest_payload(
        monkeypatch,
        {
            "schema_version": subject.BUNDLED_ROSTER_SCHEMA,
            "source": {},
            "sources": {},
            "counts": {},
            "agents": [],
        },
    )
    with pytest.raises(subject.BundledRosterError, match="agent inventory is invalid"):
        subject._validated_manifest()


@pytest.mark.parametrize(
    ("agents", "message"),
    [
        (
            [
                {"slug": "z-agent", "relative_path": "z.md", "audit_status": "retired"},
                {"slug": "a-agent", "relative_path": "a.md", "audit_status": "retired"},
            ],
            "slugs must be unique and sorted",
        ),
        (
            [
                {"slug": "a-agent", "relative_path": "same.md", "audit_status": "retired"},
                {"slug": "b-agent", "relative_path": "same.md", "audit_status": "retired"},
            ],
            "source paths must be unique",
        ),
    ],
)
def test_manifest_rejects_noncanonical_agent_inventory(
    monkeypatch: pytest.MonkeyPatch,
    agents: list[dict[str, str]],
    message: str,
) -> None:
    _install_manifest_payload(
        monkeypatch,
        {
            "schema_version": subject.BUNDLED_ROSTER_SCHEMA,
            "source": {},
            "sources": {},
            "counts": {},
            "agents": agents,
        },
    )
    monkeypatch.setattr(subject, "_validate_agent", lambda item, *, sources: item)

    with pytest.raises(subject.BundledRosterError, match=message):
        subject._validated_manifest()


def test_bundled_roster_revalidates_immutable_version_at_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = subject.bundled_manifest()
    manifest["agents"] = [
        next(item for item in manifest["agents"] if item["audit_status"] == "approved")
    ]
    validated_manifest = subject._validated_manifest
    try:
        monkeypatch.setattr(subject, "_validated_manifest", lambda: manifest)
        monkeypatch.setattr(
            subject,
            "immutable_revision_version",
            lambda _entry: "sha256:" + "0" * 64,
        )

        with pytest.raises(subject.BundledRosterError, match="immutable version does not match"):
            subject.bundled_roster()
    finally:
        subject._validated_manifest = validated_manifest


def test_bundled_contract_verification_accepts_exact_canonical_agent() -> None:
    agent = subject.bundled_roster()[0]

    assert subject.verify_bundled_agent_contract(agent, agent["prompt_body"]) is True
