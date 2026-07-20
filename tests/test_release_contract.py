from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts import (
    build_distributions,
    canonicalize_distributions,
    release_contract,
    verify_distribution,
)

ROOT = Path(__file__).resolve().parents[1]


class _FakeGit:
    def __init__(self, outputs: list[bytes] | None = None, *, failure: Exception | None = None):
        self.outputs = list(outputs or [])
        self.failure = failure
        self.arguments: list[tuple[str, ...]] = []

    def run_bytes(self, arguments: list[str]) -> bytes:
        self.arguments.append(tuple(arguments))
        if self.failure is not None:
            raise self.failure
        return self.outputs.pop(0)


def _imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_release_dependency_direction_keeps_readers_and_writers_independent() -> None:
    builder_imports = _imported_modules(ROOT / "scripts" / "build_distributions.py")
    canonicalizer_imports = _imported_modules(ROOT / "scripts" / "canonicalize_distributions.py")
    contract_imports = _imported_modules(ROOT / "scripts" / "release_contract.py")
    verifier_imports = _imported_modules(ROOT / "scripts" / "verify_distribution.py")

    assert "scripts.verify_distribution" not in builder_imports
    assert "verify_distribution" not in builder_imports
    assert "scripts.verify_distribution" not in canonicalizer_imports
    assert "verify_distribution" not in canonicalizer_imports
    assert {
        "scripts.build_distributions",
        "scripts.canonicalize_distributions",
        "scripts.release_git",
        "scripts.verify_distribution",
        "build_distributions",
        "canonicalize_distributions",
        "release_git",
        "verify_distribution",
    }.isdisjoint(contract_imports)
    assert {
        "scripts.build_distributions",
        "scripts.release_git",
        "scripts.verify_distribution",
        "build_distributions",
        "release_git",
        "verify_distribution",
    }.isdisjoint(canonicalizer_imports)
    assert {
        "scripts.build_distributions",
        "scripts.canonicalize_distributions",
        "build_distributions",
        "canonicalize_distributions",
    }.isdisjoint(verifier_imports)


def test_release_modules_share_only_the_declarative_contract() -> None:
    assert build_distributions.MAX_RELEASE_ENTRIES == release_contract.MAX_RELEASE_ENTRIES
    assert canonicalize_distributions.MAX_ARCHIVE_MEMBERS == release_contract.MAX_ARCHIVE_MEMBERS
    assert verify_distribution.CANONICAL_ZIP_METHOD == release_contract.CANONICAL_ZIP_METHOD
    assert "scripts/release_contract.py" in verify_distribution.REQUIRED_SDIST_FILES
    assert "scripts" in release_contract.RELEASE_SOURCE_PATHS
    assert "pyproject.toml" in release_contract.SDIST_ROOT_SOURCE_FILES


def test_generated_text_allowlists_are_shared_as_declarative_policy() -> None:
    assert not hasattr(release_contract, "canonical_wheel_record_payload")
    assert {
        "METADATA",
        "RECORD",
        "WHEEL",
        "entry_points.txt",
        "top_level.txt",
    } == release_contract.CANONICAL_LF_WHEEL_GENERATED_FILES
    assert {
        "PKG-INFO",
        "agency_runtime.egg-info/PKG-INFO",
        "agency_runtime.egg-info/SOURCES.txt",
        "agency_runtime.egg-info/dependency_links.txt",
        "agency_runtime.egg-info/entry_points.txt",
        "agency_runtime.egg-info/requires.txt",
        "agency_runtime.egg-info/top_level.txt",
        "setup.cfg",
    } == release_contract.CANONICAL_LF_SDIST_GENERATED_FILES


@pytest.mark.parametrize(
    "name",
    [
        "COM¹.txt",
        "COM²",
        "COM³.json",
        "LPT¹.txt",
        "LPT²",
        "LPT³.json",
        "com9.txt",
        "lpt9.txt",
    ],
)
def test_portable_names_reject_ascii_and_superscript_windows_devices(name: str) -> None:
    with pytest.raises(ValueError, match="unsafe archive member"):
        release_contract.safe_release_name(f"agency_runtime/{name}")


def test_portable_names_accept_canonical_posix_paths_and_directory_markers() -> None:
    assert release_contract.safe_release_name("agency_runtime/café.py").as_posix() == (
        "agency_runtime/café.py"
    )
    assert release_contract.safe_release_name("agency_runtime/data/").as_posix() == (
        "agency_runtime/data"
    )


@pytest.mark.parametrize(
    "name",
    [
        "",
        "a" * (release_contract.MAX_ARCHIVE_NAME_CHARS + 1),
        "agency_runtime/a\x00b.py",
        r"agency_runtime\a.py",
        "/",
        "agency_runtime//a.py",
        "agency_runtime/.",
        "agency_runtime/..",
        "agency_runtime/a.",
        "agency_runtime/a ",
        "agency_runtime/a?.py",
        "agency_runtime/a\x1f.py",
        "agency_runtime/" + ("a" * (release_contract.MAX_ARCHIVE_COMPONENT_BYTES + 1)),
        "agency_runtime/cafe\u0301.py",
        "C:/agency_runtime/a.py",
    ],
)
def test_portable_names_reject_noncanonical_or_nonportable_paths(name: str) -> None:
    with pytest.raises(ValueError, match="unsafe archive member"):
        release_contract.safe_release_name(name)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("README.md", True),
        ("agency_runtime/module.py", True),
        ("scripts/release.py", True),
        ("scripts/release.sh", False),
        ("tests/test_release.py", True),
        ("tests/dashboard_ui.test.mjs", True),
        ("tests/data.json", False),
        ("docs/guide.md", True),
        ("docs/guide.txt", False),
        ("examples/fixture.json", True),
        ("examples/fixture.md", True),
        ("examples/fixture.yaml", True),
        ("examples/fixture.yml", True),
        ("examples/fixture.exe", False),
        ("unscoped.txt", False),
    ],
)
def test_release_source_classification_is_explicit(name: str, expected: bool) -> None:
    assert release_contract.is_release_source(name) is expected


def test_release_payload_partition_is_exact() -> None:
    package, support = release_contract.partition_release_payloads(
        {
            "agency_runtime/module.py",
            "README.md",
            "scripts/release.py",
            "ignored.bin",
        }
    )

    assert package == {"agency_runtime/module.py"}
    assert support == {"README.md", "scripts/release.py"}


@pytest.mark.parametrize("commit", ["HEAD", "A" * 40, "a" * 39, "a" * 65])
def test_reviewed_checkout_rejects_noncanonical_object_ids(commit: str) -> None:
    with pytest.raises(ValueError, match="full lowercase commit"):
        release_contract.reviewed_checkout(Path("."), commit, git=_FakeGit())


@pytest.mark.parametrize("commit", ["a" * 40, "b" * 64])
def test_reviewed_checkout_accepts_clean_sha1_and_sha256_commits(commit: str) -> None:
    git = _FakeGit([commit.encode(), commit.encode(), b""])

    assert release_contract.reviewed_checkout(Path("."), commit, git=git) == commit
    assert git.arguments == [
        ("rev-parse", "--verify", f"{commit}^{{commit}}"),
        ("rev-parse", "--verify", "HEAD^{commit}"),
        (
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=none",
        ),
    ]


@pytest.mark.parametrize(
    ("outputs", "message"),
    [
        ([b"b" * 40], "expected commit is not canonical"),
        ([b"a" * 40, b"b" * 40], "live HEAD does not match"),
        ([b"a" * 40, b"a" * 40, b"dirty"], "clean Git checkout"),
    ],
)
def test_reviewed_checkout_rejects_each_state_mismatch(
    outputs: list[bytes],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        release_contract.reviewed_checkout(Path("."), "a" * 40, git=_FakeGit(outputs))


def test_reviewed_checkout_supports_verifier_owned_git_output() -> None:
    commit = "a" * 40
    outputs = iter([commit.encode(), commit.encode(), b""])
    calls: list[tuple[Path, tuple[str, ...], object | None]] = []

    def output(root: Path, arguments: list[str], *, git: object | None) -> bytes:
        calls.append((root, tuple(arguments), git))
        return next(outputs)

    marker = _FakeGit()
    assert (
        release_contract.reviewed_checkout(
            Path("repository"),
            commit,
            git=marker,
            git_output=output,
        )
        == commit
    )
    assert len(calls) == 3
    assert all(call[2] is marker for call in calls)


def test_reviewed_checkout_requires_a_session_and_wraps_transport_failures() -> None:
    with pytest.raises(ValueError, match="trusted release Git session is required"):
        release_contract.reviewed_checkout(Path("."), "a" * 40)

    git = _FakeGit(failure=RuntimeError("runner failed"))
    with pytest.raises(ValueError, match="runner failed"):
        release_contract.reviewed_checkout(Path("."), "a" * 40, git=git)
