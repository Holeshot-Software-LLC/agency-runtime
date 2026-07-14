from __future__ import annotations

from email import policy
from email.parser import BytesParser

from scripts.update_policy_availability import _referenced_slugs
from scripts.verify_distribution import (
    REQUIRED_CLASSIFIERS,
    REQUIRED_SDIST_FILES,
    _junk_failures,
    _junk_reason,
    _metadata_failures,
    _missing_file_failures,
    _payload_mismatch_failures,
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


def test_distribution_payload_helpers_preserve_failure_order_and_wording() -> None:
    assert _missing_file_failures(set(), set(), {"package.py"}) == [
        "wheel missing required files: package.py",
        "sdist missing required files: " + ", ".join(sorted({"package.py"} | REQUIRED_SDIST_FILES)),
    ]


def test_distribution_junk_and_mismatch_helpers_are_deterministic() -> None:
    assert _junk_failures("wheel", {"z.pyc", "a/__pycache__/module.py"}) == [
        "wheel contains generated junk: a/__pycache__/module.py "
        "(generated directory or file), z.pyc (generated/runtime suffix)"
    ]
    assert _payload_mismatch_failures(
        {"z.py", "a.py"},
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
    )

    assert failures[:5] == [
        "unexpected package name: 'other'",
        "version is not a normalized release version: 'local'",
        "unexpected Requires-Python: '>=3.11'",
        "unexpected license expression: None",
        f"missing classifiers: {', '.join(sorted(REQUIRED_CLASSIFIERS))}",
    ]
    assert failures[5:] == [
        "runtime dependency metadata does not constrain PyYAML to >=6.0,<7",
        "wheel missing metadata file: other-1.0.dist-info/WHEEL",
        "wheel missing metadata file: other-1.0.dist-info/RECORD",
        "wheel missing metadata file: other-1.0.dist-info/entry_points.txt",
        "wheel missing metadata file: other-1.0.dist-info/licenses/LICENSE",
        "wheel is not tagged py3-none-any",
    ]
