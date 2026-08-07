"""Fail-closed bundled-roster manifest and prompt validation tests."""

from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Iterator
from typing import Any

import pytest

from agency_runtime.core.roster import bundled as subject
from agency_runtime.core.roster.revisions import immutable_revision_version


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _entry(
    slug: str,
    *,
    status: str = "approved",
    conflicts: list[str] | None = None,
    requires: list[str] | None = None,
) -> tuple[dict[str, Any], bytes | None]:
    prompt = f"Governed instructions for {slug}.\n".encode()
    entry: dict[str, Any] = {
        "relative_path": f"engineering/{slug}.md",
        "slug": slug,
        "display_name": slug.replace("-", " ").title(),
        "division": "engineering",
        "description": f"{slug} description",
        "categories": ["engineering"],
        "capabilities": ["testing"],
        "anti_capabilities": ["unverified deployment"],
        "task_types": ["review"],
        "preferred_when": ["review is requested"],
        "avoid_when": ["evidence is unavailable"],
        "required_tools": ["tests"],
        "supported_hosts": ["codex"],
        "supported_platforms": ["windows", "linux"],
        "conflicts_with": conflicts or [],
        "requires": requires or [],
        "evidence_requirements": ["test output"],
        "model_requirements": [],
        "findings": [],
        "authority": "review",
        "context_mode": "direct_safe",
        "independence_group": "review",
        "expected_output_contract": "Return evidence-backed findings.",
        "source_revision": "a" * 40,
        "source_content_hash": "b" * 64,
        "audit_revision": "audit-v1",
        "audit_status": status,
    }
    approved = status == "approved"
    content_hash = _digest(prompt) if approved else entry["source_content_hash"]
    revision_input = {
        **entry,
        "name": entry["display_name"],
        "source": subject.SOURCE_REPOSITORY,
        "prompt_path": f"bundled://agency-agents/{slug}" if approved else "",
        "source_version": entry["source_revision"],
        "tool_affinity": entry["required_tools"],
        "hash": content_hash,
        "content": prompt.decode() if approved else "",
    }
    entry.update(
        version=immutable_revision_version(revision_input),
        prompt_file=f"prompts/{slug}.txt" if approved else None,
        prompt_hash=content_hash if approved else None,
    )
    return entry, prompt if approved else None


def _files(entries_with_prompts: list[tuple[dict[str, Any], bytes | None]]) -> dict[str, bytes]:
    entries = sorted(
        (entry for entry, _prompt in entries_with_prompts), key=lambda item: item["slug"]
    )
    license_bytes = b"MIT License\n"
    manifest = {
        "schema_version": subject.BUNDLED_ROSTER_SCHEMA,
        "source": {
            "repository": subject.SOURCE_REPOSITORY,
            "revision": "a" * 40,
            "license": subject.SOURCE_LICENSE,
            "license_file": subject.SOURCE_LICENSE_FILE,
            "license_hash": _digest(license_bytes),
        },
        "counts": {
            "total": len(entries),
            "approved": sum(item["audit_status"] == "approved" for item in entries),
            "quarantined": sum(item["audit_status"] == "quarantined" for item in entries),
            "retired": sum(item["audit_status"] == "retired" for item in entries),
        },
        "agents": entries,
    }
    manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    files = {
        "manifest.json": manifest_bytes,
        "manifest.sha256": (_digest(manifest_bytes) + "\n").encode(),
        subject.SOURCE_LICENSE_FILE: license_bytes,
    }
    for entry, prompt in entries_with_prompts:
        if prompt is not None:
            files[str(entry["prompt_file"])] = prompt
    return files


def _rewrite_manifest(files: dict[str, bytes], mutate: Any) -> None:
    manifest = json.loads(files["manifest.json"])
    mutate(manifest)
    payload = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    files["manifest.json"] = payload
    files["manifest.sha256"] = (_digest(payload) + "\n").encode()


def _rewrite_approved_entry(
    files: dict[str, bytes],
    mutate: Any,
    *,
    prompt: str | None = None,
) -> None:
    def update(manifest: dict[str, Any]) -> None:
        entry = manifest["agents"][0]
        mutate(entry)
        if prompt is not None:
            prompt_bytes = prompt.encode()
            files[str(entry["prompt_file"])] = prompt_bytes
            entry["prompt_hash"] = _digest(prompt_bytes)
        prompt_body = files[str(entry["prompt_file"])].decode()
        entry["version"] = immutable_revision_version(
            subject._revision_input(
                entry,
                manifest["source"],
                prompt_body=prompt_body,
                content_hash=entry["prompt_hash"],
            )
        )

    _rewrite_manifest(files, update)


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    subject.clear_bundled_roster_cache()
    yield
    subject.clear_bundled_roster_cache()


def _install_resources(monkeypatch: pytest.MonkeyPatch, files: dict[str, bytes]) -> None:
    def resource(relative_path: str, *, limit: int, label: str) -> bytes:
        try:
            data = files[relative_path]
        except KeyError as exc:
            raise subject.BundledRosterError(f"{label} is unavailable") from exc
        if len(data) > limit:
            raise subject.BundledRosterError(f"{label} exceeds its packaged size limit")
        return data

    monkeypatch.setattr(subject, "_resource", resource)


def test_valid_bundle_is_lazy_defensive_and_excludes_quarantine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alpha = _entry("alpha-agent")
    quarantine = _entry("unsafe-agent", status="quarantined")
    files = _files([alpha, quarantine])
    _install_resources(monkeypatch, files)

    manifest = subject.bundled_manifest()
    assert manifest["counts"] == {
        "total": 2,
        "approved": 1,
        "quarantined": 1,
        "retired": 0,
    }
    manifest["agents"].clear()
    assert len(subject.bundled_manifest()["agents"]) == 2

    roster = subject.BundledRoster()
    assert len(roster) == 1
    assert roster[0]["slug"] == "alpha-agent"
    assert roster[:][0]["prompt_body"] == alpha[1].decode()
    assert [item["slug"] for item in roster] == ["alpha-agent"]


def test_packaged_license_is_canonical_lf_and_bound_to_upstream_blob() -> None:
    manifest = subject.bundled_manifest()
    license_bytes = subject._resource(
        subject.SOURCE_LICENSE_FILE,
        limit=subject.MAX_LICENSE_BYTES,
        label="bundled roster license",
    )

    assert b"\r" not in license_bytes
    assert _digest(license_bytes) == manifest["source"]["license_hash"]
    assert manifest["source"]["license_hash"] == (
        "9a45258434d5cedf0af73c9ad4771373701225038d246c49219026c33677f66f"
    )


def test_bundle_rejects_manifest_and_prompt_tampering(monkeypatch: pytest.MonkeyPatch) -> None:
    files = _files([_entry("alpha-agent")])
    files["manifest.sha256"] = b"0" * 64
    _install_resources(monkeypatch, files)
    with pytest.raises(subject.BundledRosterError, match="manifest digest"):
        subject.bundled_manifest()

    subject.clear_bundled_roster_cache()
    files = _files([_entry("alpha-agent")])
    files["prompts/alpha-agent.txt"] = b"tampered"
    _install_resources(monkeypatch, files)
    with pytest.raises(subject.BundledRosterError, match="prompt hash"):
        subject.bundled_manifest()


def test_bundle_rejects_c1_in_manifest_text(monkeypatch: pytest.MonkeyPatch) -> None:
    files = _files([_entry("alpha-agent")])
    _rewrite_manifest(
        files,
        lambda manifest: manifest["agents"][0].update(description="unsafe \x80 text"),
    )
    _install_resources(monkeypatch, files)

    with pytest.raises(subject.BundledRosterError, match=r"description.*invalid"):
        subject.bundled_manifest()


def test_bundle_rejects_resigned_cf_in_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    files = _files([_entry("alpha-agent")])
    _rewrite_approved_entry(
        files,
        lambda _entry: None,
        prompt="Governed\u200b instructions for alpha-agent.\n",
    )
    _install_resources(monkeypatch, files)

    with pytest.raises(
        subject.BundledRosterError,
        match="prompt contains unsafe controls or suspicious encoding",
    ):
        subject.bundled_manifest()


def test_bundle_prompt_safety_preserves_allowed_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _files([_entry("alpha-agent")])
    prompt = "\tGoverned instructions for alpha-agent.\r\nSecond line.\n"
    _rewrite_approved_entry(files, lambda _entry: None, prompt=prompt)
    _install_resources(monkeypatch, files)

    assert subject.BundledRoster()[0]["prompt_body"] == prompt


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda entry: entry.update(display_name="Alpha\u200b Agent"), "display_name.*invalid"),
        (
            lambda entry: entry.update(capabilities=["test\u200bing"]),
            "capabilities.*invalid",
        ),
        (
            lambda entry: entry.update(relative_path="engineering/alpha\u200b-agent.md"),
            "relative_path.*invalid",
        ),
    ],
)
def test_bundle_rejects_resigned_cf_in_manifest_metadata_and_paths(
    monkeypatch: pytest.MonkeyPatch,
    mutation: Any,
    message: str,
) -> None:
    files = _files([_entry("alpha-agent")])
    _rewrite_approved_entry(files, mutation)
    _install_resources(monkeypatch, files)

    with pytest.raises(subject.BundledRosterError, match=message):
        subject.bundled_manifest()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data["source"].update(repository="https://invalid.example"), "provenance"),
        (lambda data: data["source"].update(extra="value"), "provenance"),
        (lambda data: data["source"].update(license_file="other.txt"), "license path"),
        (lambda data: data["counts"].update(total=99), "status counts"),
        (lambda data: data["counts"].update(total=True), "status counts"),
        (lambda data: data.update(schema_version=True), "schema is unsupported"),
        (lambda data: data.update(extra="value"), "schema is unsupported"),
        (lambda data: data["agents"][0].update(extra="value"), "agent entry"),
        (lambda data: data["agents"][0].update(authority="owner"), "authority"),
        (lambda data: data["agents"][0].update(context_mode="shared"), "context mode"),
        (lambda data: data["agents"][0].update(prompt_file="../escape.txt"), "safe package"),
        (lambda data: data["agents"][0].update(relative_path="engineering/con.md"), "safe package"),
        (lambda data: data["agents"][0].update(capabilities=["unsafe\nvalue"]), "list"),
        (lambda data: data["agents"][0].update(capabilities=[]), "incomplete"),
        (lambda data: data["agents"][0].update(supported_hosts=[]), "no execution target"),
    ],
)
def test_bundle_rejects_invalid_manifest_contracts(
    monkeypatch: pytest.MonkeyPatch,
    mutation: Any,
    message: str,
) -> None:
    files = _files([_entry("alpha-agent")])
    _rewrite_manifest(files, mutation)
    _install_resources(monkeypatch, files)

    with pytest.raises(subject.BundledRosterError, match=message):
        subject.bundled_manifest()


def test_bundle_rejects_asymmetric_conflicts_and_requirement_cycles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _files(
        [
            _entry("alpha-agent", conflicts=["beta-agent"]),
            _entry("beta-agent"),
        ]
    )
    _install_resources(monkeypatch, files)
    with pytest.raises(subject.BundledRosterError, match="not symmetric"):
        subject.bundled_manifest()

    subject.clear_bundled_roster_cache()
    files = _files(
        [
            _entry("alpha-agent", requires=["beta-agent"]),
            _entry("beta-agent", requires=["alpha-agent"]),
        ]
    )
    _install_resources(monkeypatch, files)
    with pytest.raises(subject.BundledRosterError, match="requirement cycle"):
        subject.bundled_manifest()


def test_bundle_rejects_approved_dependency_on_quarantine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _files(
        [
            _entry("alpha-agent", requires=["unsafe-agent"]),
            _entry("unsafe-agent", status="quarantined"),
        ]
    )
    _install_resources(monkeypatch, files)

    with pytest.raises(subject.BundledRosterError, match="requires an inactive agent"):
        subject.bundled_manifest()


def test_bundle_rejects_immutable_version_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    files = _files([_entry("alpha-agent")])
    _rewrite_manifest(files, lambda data: data["agents"][0].update(version="sha256:" + "f" * 64))
    _install_resources(monkeypatch, files)

    with pytest.raises(subject.BundledRosterError, match="immutable version does not match"):
        subject.bundled_manifest()


def test_resource_streams_at_most_limit_plus_one(monkeypatch: pytest.MonkeyPatch) -> None:
    reads: list[int] = []

    class Stream(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            reads.append(size)
            return super().read(size)

    class Node:
        def joinpath(self, _part: str) -> Node:
            return self

        def open(self, _mode: str) -> Stream:
            return Stream(b"oversized")

    monkeypatch.setattr(subject.resources, "files", lambda _package: Node())

    with pytest.raises(subject.BundledRosterError, match="exceeds"):
        subject._resource("manifest.json", limit=4, label="manifest")

    assert reads == [5]
