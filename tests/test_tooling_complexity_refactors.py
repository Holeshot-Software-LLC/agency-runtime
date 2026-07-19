from __future__ import annotations

from email import policy
from email.parser import BytesParser

from scripts import update_policy_availability
from scripts.update_policy_availability import _referenced_slugs
from scripts.verify_distribution import (
    REQUIRED_CLASSIFIERS,
    REQUIRED_SDIST_FILES,
    _junk_failures,
    _junk_reason,
    _metadata_failures,
    _missing_file_failures,
    _partition_release_payloads,
    _payload_mismatch_failures,
    _unexpected_scoped_payload_failures,
)


def test_referenced_slugs_preserves_supported_policy_shapes() -> None:
    policy = {
        "actions": {
            "valid": {
                "always_include": [{"slug": "reviewer"}, {"slug": 7}, {}],
                "conditional": [{"slug": "writer"}, ["ignored"]],
            },
            "invalid": ["ignored"],
        },
        "division_anchors": {
            "valid": {
                "anchor": "engineering",
                "conditional": [
                    ["developer", "condition"],
                    ("tester", "condition"),
                    {"slug": "architect"},
                    [],
                    {"slug": ""},
                ],
            },
            "invalid": "ignored",
        },
    }

    assert _referenced_slugs(policy) == {
        "7",
        "architect",
        "developer",
        "engineering",
        "reviewer",
        "tester",
        "writer",
    }


def test_referenced_slugs_ignores_malformed_collections() -> None:
    assert (
        _referenced_slugs({"actions": [], "division_anchors": {"bad": {"conditional": "invalid"}}})
        == set()
    )


def test_policy_availability_ignores_bundled_semantic_only_agents(
    monkeypatch,
) -> None:
    policy_document = {
        "actions": {
            "TEST": {
                "always_include": [{"slug": "static-agent"}],
                "conditional": [{"slug": "missing-agent", "when": "missing"}],
            }
        }
    }
    monkeypatch.setattr(
        update_policy_availability,
        "BUNDLED",
        ("semantic-only-agent", "static-agent"),
    )

    rendered = update_policy_availability._render(policy_document)

    assert "  - static-agent" in rendered
    assert "    - missing-agent" in rendered
    assert "semantic-only-agent" not in rendered


def test_policy_availability_renders_empty_collections_as_yaml_lists(
    monkeypatch,
) -> None:
    policy_document = {
        "actions": {
            "TEST": {
                "always_include": [{"slug": "static-agent"}],
                "conditional": [],
            }
        }
    }
    monkeypatch.setattr(update_policy_availability, "BUNDLED", ("static-agent",))

    fully_available = update_policy_availability._render(policy_document)
    monkeypatch.setattr(update_policy_availability, "BUNDLED", ())
    fully_gated = update_policy_availability._render(policy_document)

    assert "    slugs: []" in fully_available
    assert "  enabled: []" in fully_gated


def test_distribution_payload_helpers_preserve_failure_order_and_wording() -> None:
    assert _missing_file_failures(set(), set(), {"package.py"}) == [
        "wheel missing required files: package.py",
        "sdist missing required files: " + ", ".join(sorted({"package.py"} | REQUIRED_SDIST_FILES)),
    ]


def test_distribution_payload_manifest_is_commit_scoped_and_exact() -> None:
    package, support = _partition_release_payloads(
        {
            "agency_runtime/current.py",
            "scripts/release.py",
            "tests/test_release.py",
            "README.md",
        }
    )
    assert package == {"agency_runtime/current.py"}
    assert support == {"README.md", "scripts/release.py", "tests/test_release.py"}

    assert _missing_file_failures(
        {"agency_runtime/current.py"},
        {"agency_runtime/current.py", "scripts/release.py"},
        package,
        support | {"tests/test_release.py"},
    ) == ["sdist missing required files: README.md, tests/test_release.py"]
    assert _unexpected_scoped_payload_failures(
        "wheel",
        {"agency_runtime/current.py", "agency_runtime/stale.py", "metadata/METADATA"},
        package,
        prefixes=("agency_runtime/",),
    ) == ["wheel contains unexpected source payload: agency_runtime/stale.py"]
    assert (
        _unexpected_scoped_payload_failures(
            "wheel",
            {"agency_runtime/current.py"},
            package,
            prefixes=("agency_runtime/",),
        )
        == []
    )


def test_distribution_junk_and_mismatch_helpers_are_deterministic() -> None:
    assert _junk_failures("wheel", {"z.pyc", "a/__pycache__/module.py"}) == [
        "wheel contains generated junk: a/__pycache__/module.py "
        "(generated directory or file), z.pyc (generated/runtime suffix)"
    ]
    assert _payload_mismatch_failures(
        {"z.py", "a.py", "missing.py"},
        {"a.py": b"wheel", "z.py": b"same"},
        {"a.py": b"sdist", "z.py": b"same"},
    ) == ["wheel/sdist payload mismatch: a.py"]


def test_distribution_junk_rejects_secret_and_sqlite_sidecar_families() -> None:
    assert _junk_reason(".env.production") == "environment secret file"
    assert _junk_reason("runtime.sqlite3") == "generated/runtime suffix"
    assert _junk_reason("runtime.db-wal") == "generated/runtime sidecar"
    assert _junk_reason(".env.example") is None


def test_distribution_metadata_helper_preserves_policy_failure_order() -> None:
    metadata = BytesParser(policy=policy.default).parsebytes(
        b"Name: other\nVersion: local\nRequires-Python: >=3.11\n\n"
    )

    failures = _metadata_failures(
        "other-1.0.dist-info/METADATA",
        metadata,
        {"other-1.0.dist-info/METADATA"},
        {},
        expected_version="0.1.0",
        expected_dependencies=("pyyaml<7,>=6.0",),
        expected_license=b"",
    )

    assert failures[:7] == [
        "wheel METADATA must contain exactly one Metadata-Version header",
        "wheel METADATA has unexpected Name: 'other'",
        "wheel METADATA has unexpected Version: 'local'",
        "wheel METADATA has unexpected Requires-Python: '>=3.11'",
        "wheel METADATA must contain exactly one License-Expression header",
        "wheel METADATA dependency metadata does not match committed pyproject",
        f"missing classifiers: {', '.join(sorted(REQUIRED_CLASSIFIERS))}",
    ]
    assert failures[7:] == [
        "unexpected wheel metadata path: other-1.0.dist-info/METADATA",
        "wheel missing metadata file: agency_runtime-0.1.0.dist-info/RECORD",
        "wheel missing metadata file: agency_runtime-0.1.0.dist-info/WHEEL",
        "wheel missing metadata file: agency_runtime-0.1.0.dist-info/entry_points.txt",
        "wheel missing metadata file: agency_runtime-0.1.0.dist-info/licenses/LICENSE",
        "wheel missing metadata file: agency_runtime-0.1.0.dist-info/top_level.txt",
    ]
