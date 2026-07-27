"""Versioned, exact-match timing weights for the local Windows pytest loop."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from scripts.parallel_change_loop_runtime import RUNTIME_CONTRACT_VERSION
from scripts.pytest_file_timing import MAX_RUN_TIMING_BYTES, RUN_TIMING_SCHEMA
from scripts.select_test_shard import discover_test_files, partition_test_files

PROFILE_SCHEMA = "agency.pytest-shard-weights.v1"
PROFILE_RELATIVE_PATH = Path("scripts/test_shard_weights/windows-cpython313-v1.json")
DEFAULT_PARTITION_STRATEGY = "source-bytes"
CORPUS_ID = "warning-strict-not-performance-v1"
METRIC_ID = "setup-call-teardown-ns"
AGGREGATION_ID = "median"
MAX_PROFILE_BYTES = 1024 * 1024
MAX_PROFILE_FILES = 4096
MAX_TEST_FILE_BYTES = 8 * 1024 * 1024
MAX_HARNESS_FILE_BYTES = 8 * 1024 * 1024
MAX_WEIGHT_NS = 2**63 - 1
MIN_PROFILE_SAMPLES = 3
MAX_PROFILE_SAMPLES = 9

_HEX_32 = re.compile(r"[a-f0-9]{32}")
_HEX_40 = re.compile(r"[a-f0-9]{40}")
_HEX_64 = re.compile(r"[a-f0-9]{64}")
_VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z.!+_-]{0,63}")
_HARNESS_PATHS = (
    "pyproject.toml",
    "scripts/ci_private_node.py",
    "scripts/parallel_change_loop_runtime.py",
    "scripts/parallel_change_loop_storage.py",
    "scripts/prepare_ci_runtime.py",
    "scripts/pytest_file_timing.py",
    "scripts/run_parallel_change_loop.py",
    "scripts/select_test_shard.py",
    "scripts/test_shard_profile.py",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/runtime_support.py",
)
_MEASUREMENT_KEYS = {
    "architecture",
    "content_set_sha256",
    "corpus",
    "harness_sha256",
    "metric",
    "path_set_sha256",
    "platform",
    "pytest_version",
    "python_implementation",
    "python_minor",
    "product_source_sha256",
    "relevant_tree_clean",
    "repository_commit",
    "runtime_contract_version",
    "runtime_key",
    "test_root",
    "worker_count",
}
_PARTITION_KEYS = {
    "algorithm",
    "assignment_sha256",
    "profile_digest",
    "profile_path",
    "reason",
    "requested",
    "shards",
    "source_run_ids",
    "status",
}


@dataclass(frozen=True, slots=True)
class PartitionWeights:
    """A complete weight map plus bounded observability for its provenance."""

    weights: Mapping[Path, int] = field(repr=False)
    algorithm: str
    status: str
    reason: str
    requested: str
    profile_digest: str | None = None
    profile_path: str | None = None
    source_run_ids: tuple[str, ...] = ()

    def preview(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "profile_digest": self.profile_digest,
            "profile_path": self.profile_path,
            "reason": self.reason,
            "requested": self.requested,
            "source_run_ids": list(self.source_run_ids),
            "status": self.status,
        }


def _positive_integer(value: object, *, label: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{label} must be a bounded positive integer")
    return value


def _nonnegative_integer(value: object, *, label: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError(f"{label} must be a bounded nonnegative integer")
    return value


def _exact_mapping(value: object, keys: set[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} has an invalid shape")
    return value


def _canonical_repository_test_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 512
        or "\\" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError("pytest path is not bounded canonical text")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or not path.name.startswith("test_")
        or path.suffix != ".py"
    ):
        raise ValueError("pytest path is not canonical")
    return value


def _canonical_profile_path(value: object) -> str:
    canonical = _canonical_repository_test_path(value)
    if len(PurePosixPath(canonical).parts) < 2 or not canonical.startswith("tests/"):
        raise ValueError("profile test path is outside the canonical test root")
    return canonical


def _canonical_test_root(value: str) -> str:
    if value == ".":
        return value
    if (
        not value
        or len(value) > 512
        or "\\" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError("test root is not bounded canonical text")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError("test root is not canonical")
    return value


def _hash_file(path: Path, *, maximum_bytes: int, label: str) -> tuple[str, int]:
    raw = read_bounded_regular_file(path, limit=maximum_bytes, label=label)
    return hashlib.sha256(raw).hexdigest(), len(raw)


def _feed_length_prefixed(digest: Any, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _path_set_digest(paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for value in sorted(paths):
        _feed_length_prefixed(digest, value.encode("utf-8"))
    return digest.hexdigest()


def _content_set_digest(records: Mapping[str, str]) -> str:
    digest = hashlib.sha256()
    for path, source_digest in sorted(records.items()):
        _feed_length_prefixed(digest, path.encode("utf-8"))
        _feed_length_prefixed(digest, bytes.fromhex(source_digest))
    return digest.hexdigest()


def _harness_digest(
    repo_root: Path,
    *,
    worker_count: int,
    pytest_flags: Sequence[str],
) -> str:
    semantics = json.dumps(
        {
            "corpus": CORPUS_ID,
            "metric": METRIC_ID,
            "pytest_flags": list(pytest_flags),
            "runtime_contract_version": RUNTIME_CONTRACT_VERSION,
            "worker_count": worker_count,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    digest = hashlib.sha256()
    _feed_length_prefixed(digest, semantics)
    for relative in _HARNESS_PATHS:
        _feed_length_prefixed(digest, relative.encode("ascii"))
        path = repo_root / Path(relative)
        if not path.exists():
            _feed_length_prefixed(digest, b"missing")
            continue
        source_digest, _size = _hash_file(
            path,
            maximum_bytes=MAX_HARNESS_FILE_BYTES,
            label=f"timing harness {relative}",
        )
        _feed_length_prefixed(digest, bytes.fromhex(source_digest))
    return digest.hexdigest()


def _product_source_digest(repo_root: Path) -> str:
    product_root = repo_root / "agency_runtime"
    paths = [] if not product_root.exists() else sorted(product_root.rglob("*"))
    files = [
        path
        for path in paths
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix.casefold() not in {".pyc", ".pyo"}
    ]
    if len(files) > MAX_PROFILE_FILES:
        raise ValueError("product source inventory is outside its bound")
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(repo_root).as_posix()
        source_digest, _size = _hash_file(
            path,
            maximum_bytes=MAX_HARNESS_FILE_BYTES,
            label=f"product source {relative}",
        )
        _feed_length_prefixed(digest, relative.encode("utf-8"))
        _feed_length_prefixed(digest, bytes.fromhex(source_digest))
    return digest.hexdigest()


def _repository_state(repo_root: Path) -> tuple[str | None, bool]:
    try:
        commit = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        status = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--",
                "agency_runtime",
                "tests",
                "scripts",
                "pyproject.toml",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None, False
    value = commit.stdout.strip()
    if commit.returncode != 0 or not _HEX_40.fullmatch(value) or status.returncode != 0:
        return None, False
    return value, not status.stdout


def _test_inventory(
    repo_root: Path,
    test_files: Sequence[Path],
) -> tuple[dict[str, Path], dict[str, str], dict[str, int]]:
    paths: dict[str, Path] = {}
    digests: dict[str, str] = {}
    sizes: dict[str, int] = {}
    casefolded: set[str] = set()
    for raw_path in test_files:
        path = raw_path.resolve(strict=True)
        try:
            relative = path.relative_to(repo_root).as_posix()
        except ValueError as exc:
            raise ValueError("pytest file escaped the repository") from exc
        canonical = _canonical_repository_test_path(relative)
        folded = canonical.casefold()
        if canonical in paths or folded in casefolded:
            raise ValueError("pytest file inventory contains a path collision")
        source_digest, source_bytes = _hash_file(
            path,
            maximum_bytes=MAX_TEST_FILE_BYTES,
            label=f"pytest source {canonical}",
        )
        paths[canonical] = path
        digests[canonical] = source_digest
        sizes[canonical] = source_bytes
        casefolded.add(folded)
    if not 1 <= len(paths) <= MAX_PROFILE_FILES:
        raise ValueError("pytest file inventory is outside its bound")
    return paths, digests, sizes


def build_measurement_context(
    repo_root: Path,
    test_files: Sequence[Path],
    *,
    worker_count: int,
    pytest_flags: Sequence[str],
    runtime_key: str,
    test_root: str = "tests",
    platform_name: str | None = None,
    architecture: str | None = None,
    python_implementation: str | None = None,
    python_minor: str | None = None,
    pytest_version: str | None = None,
) -> dict[str, Any]:
    """Bind a timing run to its exact corpus, harness, and runtime family."""

    repo = repo_root.resolve(strict=True)
    count = _positive_integer(worker_count, label="worker_count", maximum=MAX_PROFILE_FILES)
    if not _HEX_64.fullmatch(runtime_key):
        raise ValueError("runtime_key must be a SHA-256 digest")
    paths, digests, _sizes = _test_inventory(repo, test_files)
    repository_commit, relevant_tree_clean = _repository_state(repo)
    resolved_platform = sys.platform if platform_name is None else platform_name
    resolved_architecture = platform.machine() if architecture is None else architecture
    resolved_implementation = (
        platform.python_implementation() if python_implementation is None else python_implementation
    )
    resolved_minor = (
        f"{sys.version_info.major}.{sys.version_info.minor}"
        if python_minor is None
        else python_minor
    )
    resolved_pytest = (
        importlib.metadata.version("pytest") if pytest_version is None else pytest_version
    )
    text_values = {
        "architecture": resolved_architecture.casefold(),
        "platform": resolved_platform.casefold(),
        "pytest_version": resolved_pytest,
        "python_implementation": resolved_implementation.casefold(),
        "python_minor": resolved_minor,
    }
    if any(
        not value or len(value) > 64 or any(ord(character) < 32 for character in value)
        for value in text_values.values()
    ) or not _VERSION.fullmatch(text_values["pytest_version"]):
        raise ValueError("timing runtime identity contains invalid text")
    return {
        "architecture": text_values["architecture"],
        "content_set_sha256": _content_set_digest(digests),
        "corpus": CORPUS_ID,
        "harness_sha256": _harness_digest(
            repo,
            worker_count=count,
            pytest_flags=pytest_flags,
        ),
        "metric": METRIC_ID,
        "path_set_sha256": _path_set_digest(tuple(paths)),
        "platform": text_values["platform"],
        "pytest_version": text_values["pytest_version"],
        "python_implementation": text_values["python_implementation"],
        "python_minor": text_values["python_minor"],
        "product_source_sha256": _product_source_digest(repo),
        "relevant_tree_clean": relevant_tree_clean,
        "repository_commit": repository_commit,
        "runtime_contract_version": RUNTIME_CONTRACT_VERSION,
        "runtime_key": runtime_key,
        "test_root": _canonical_test_root(test_root),
        "worker_count": count,
    }


def _byte_weights(
    test_files: Sequence[Path],
    *,
    requested: str,
    status: str,
    reason: str,
) -> PartitionWeights:
    return PartitionWeights(
        weights={path: max(1, path.stat().st_size) for path in test_files},
        algorithm="source-bytes-lpt-v1",
        status=status,
        reason=reason,
        requested=requested,
    )


def _validated_profile(
    payload: object,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, tuple[str, int, int]]]:
    root = _exact_mapping(payload, {"files", "profile", "schema", "source"}, label="profile")
    if root["schema"] != PROFILE_SCHEMA:
        raise ValueError("profile schema is unsupported")
    profile_data = _exact_mapping(
        root["profile"],
        {
            "aggregation",
            "architecture",
            "corpus",
            "metric",
            "platform",
            "pytest_version",
            "python_implementation",
            "python_minor",
            "runtime_contract_version",
            "sample_count",
            "worker_count",
        },
        label="profile runtime",
    )
    source = _exact_mapping(
        root["source"],
        {
            "content_set_sha256",
            "evidence_artifact_sha256",
            "evidence_commit",
            "evidence_run_ids",
            "evidence_runtime_keys",
            "harness_sha256",
            "path_set_sha256",
            "product_source_sha256",
            "test_file_count",
            "test_root",
        },
        label="profile source",
    )
    sample_count = _positive_integer(
        profile_data["sample_count"],
        label="sample_count",
        maximum=MAX_PROFILE_SAMPLES,
    )
    if sample_count < MIN_PROFILE_SAMPLES or sample_count % 2 == 0:
        raise ValueError("profile sample count must be an odd production sample")
    if (
        profile_data["aggregation"] != AGGREGATION_ID
        or profile_data["corpus"] != CORPUS_ID
        or profile_data["metric"] != METRIC_ID
        or profile_data["runtime_contract_version"] != RUNTIME_CONTRACT_VERSION
    ):
        raise ValueError("profile runtime contract is unsupported")
    for key in (
        "architecture",
        "platform",
        "pytest_version",
        "python_implementation",
        "python_minor",
    ):
        value = profile_data[key]
        if not isinstance(value, str) or not value or len(value) > 64:
            raise ValueError("profile runtime identity is invalid")
    _positive_integer(
        profile_data["worker_count"],
        label="profile worker count",
        maximum=MAX_PROFILE_FILES,
    )
    for key in (
        "content_set_sha256",
        "harness_sha256",
        "path_set_sha256",
        "product_source_sha256",
    ):
        if not isinstance(source[key], str) or not _HEX_64.fullmatch(source[key]):
            raise ValueError("profile source digest is invalid")
    if source["test_root"] != "tests" or not _HEX_40.fullmatch(str(source["evidence_commit"])):
        raise ValueError("profile source identity is invalid")
    file_count = _positive_integer(
        source["test_file_count"],
        label="profile file count",
        maximum=MAX_PROFILE_FILES,
    )
    run_ids = source["evidence_run_ids"]
    artifact_digests = source["evidence_artifact_sha256"]
    runtime_keys = source["evidence_runtime_keys"]
    if (
        not isinstance(run_ids, list)
        or not isinstance(artifact_digests, list)
        or not isinstance(runtime_keys, list)
        or len(run_ids) != sample_count
        or len(artifact_digests) != sample_count
        or len(runtime_keys) != sample_count
        or len(set(run_ids)) != sample_count
        or any(not isinstance(value, str) or not _HEX_32.fullmatch(value) for value in run_ids)
        or any(
            not isinstance(value, str) or not _HEX_64.fullmatch(value)
            for value in (*artifact_digests, *runtime_keys)
        )
    ):
        raise ValueError("profile evidence identity is invalid")
    raw_files = root["files"]
    if not isinstance(raw_files, list) or len(raw_files) != file_count:
        raise ValueError("profile file records are invalid")
    records: dict[str, tuple[str, int, int]] = {}
    casefolded: set[str] = set()
    for raw_record in raw_files:
        record = _exact_mapping(
            raw_record,
            {"path", "source_bytes", "source_sha256", "weight_ns"},
            label="profile file record",
        )
        path = _canonical_profile_path(record["path"])
        folded = path.casefold()
        if path in records or folded in casefolded:
            raise ValueError("profile contains a duplicate or case-colliding path")
        source_sha256 = record["source_sha256"]
        if not isinstance(source_sha256, str) or not _HEX_64.fullmatch(source_sha256):
            raise ValueError("profile file digest is invalid")
        source_bytes = _nonnegative_integer(
            record["source_bytes"],
            label="profile source bytes",
            maximum=MAX_TEST_FILE_BYTES,
        )
        weight_ns = _positive_integer(
            record["weight_ns"],
            label="profile weight",
            maximum=MAX_WEIGHT_NS,
        )
        records[path] = (source_sha256, source_bytes, weight_ns)
        casefolded.add(folded)
    if (
        _path_set_digest(tuple(records)) != source["path_set_sha256"]
        or _content_set_digest({path: record[0] for path, record in records.items()})
        != source["content_set_sha256"]
    ):
        raise ValueError("profile inventory digest is inconsistent")
    return profile_data, source, records


def _read_profile(
    path: Path,
) -> tuple[bytes, dict[str, Any], dict[str, Any], dict[str, tuple[str, int, int]]]:
    raw = read_bounded_regular_file(
        path,
        limit=MAX_PROFILE_BYTES,
        label="pytest shard weight profile",
    )
    payload = safe_load_bounded_json(
        raw,
        maximum_bytes=MAX_PROFILE_BYTES,
        maximum_depth=8,
        maximum_nodes=MAX_PROFILE_FILES * 8,
    )
    profile_data, source, records = _validated_profile(payload)
    return raw, profile_data, source, records


def load_partition_weights(
    repo_root: Path,
    test_files: Sequence[Path],
    *,
    worker_count: int,
    pytest_flags: Sequence[str],
    runtime_key: str,
    test_root: str = "tests",
    strategy: str = DEFAULT_PARTITION_STRATEGY,
    require_exact: bool = False,
    platform_name: str | None = None,
    architecture: str | None = None,
    python_implementation: str | None = None,
    python_minor: str | None = None,
    pytest_version: str | None = None,
) -> PartitionWeights:
    """Load exact Windows timing weights or visibly fall back to source bytes."""

    if strategy not in {"auto", "source-bytes"}:
        raise ValueError("partition strategy is unsupported")
    if require_exact and strategy != "auto":
        raise ValueError("exact shard weights require the automatic strategy")
    requested = "exact-timing" if require_exact else strategy
    if strategy == "source-bytes":
        return _byte_weights(
            test_files,
            requested=requested,
            status="disabled",
            reason="explicit-source-bytes",
        )
    if _canonical_test_root(test_root) != "tests":
        if require_exact:
            raise RuntimeError("exact shard weights require the canonical test root")
        return _byte_weights(
            test_files,
            requested=requested,
            status="unsupported",
            reason="custom-test-root",
        )
    resolved_platform = (sys.platform if platform_name is None else platform_name).casefold()
    resolved_implementation = (
        platform.python_implementation() if python_implementation is None else python_implementation
    ).casefold()
    if resolved_platform != "win32" or resolved_implementation != "cpython":
        if require_exact:
            raise RuntimeError("exact shard weights are unsupported on this runtime")
        return _byte_weights(
            test_files,
            requested=requested,
            status="unsupported",
            reason="unsupported-runtime",
        )
    repo = repo_root.resolve(strict=True)
    profile_path = repo / PROFILE_RELATIVE_PATH
    try:
        raw, profile_data, source, records = _read_profile(profile_path)
    except FileNotFoundError:
        if require_exact:
            raise RuntimeError("exact shard weight profile is missing") from None
        return _byte_weights(
            test_files,
            requested=requested,
            status="missing",
            reason="profile-missing",
        )
    except (OSError, TypeError, ValueError) as exc:
        if require_exact:
            raise RuntimeError("exact shard weight profile is invalid") from exc
        return _byte_weights(
            test_files,
            requested=requested,
            status="invalid",
            reason="profile-invalid",
        )
    context = build_measurement_context(
        repo_root,
        test_files,
        worker_count=worker_count,
        pytest_flags=pytest_flags,
        runtime_key=runtime_key,
        test_root=test_root,
        platform_name=platform_name,
        architecture=architecture,
        python_implementation=python_implementation,
        python_minor=python_minor,
        pytest_version=pytest_version,
    )
    current_paths, current_digests, current_sizes = _test_inventory(repo, test_files)
    expected_runtime = {
        "architecture": context["architecture"],
        "corpus": context["corpus"],
        "metric": context["metric"],
        "platform": context["platform"],
        "pytest_version": context["pytest_version"],
        "python_implementation": context["python_implementation"],
        "python_minor": context["python_minor"],
        "runtime_contract_version": context["runtime_contract_version"],
        "worker_count": context["worker_count"],
    }
    observed_runtime = {key: profile_data[key] for key in expected_runtime}
    compatible = bool(
        observed_runtime == expected_runtime
        and source["test_root"] == context["test_root"]
        and source["test_file_count"] == len(current_paths)
        and source["path_set_sha256"] == context["path_set_sha256"]
        and source["content_set_sha256"] == context["content_set_sha256"]
        and source["harness_sha256"] == context["harness_sha256"]
        and set(records) == set(current_paths)
        and all(
            records[path][0] == current_digests[path] and records[path][1] == current_sizes[path]
            for path in current_paths
        )
    )
    if not compatible:
        if require_exact:
            raise RuntimeError("exact shard weight profile is stale")
        return _byte_weights(
            test_files,
            requested=requested,
            status="stale",
            reason="profile-stale",
        )
    exact = source["product_source_sha256"] == context["product_source_sha256"]
    if require_exact and not exact:
        raise RuntimeError("exact shard weight profile is stale")
    weights = {current_paths[path]: records[path][2] for path in current_paths}
    return PartitionWeights(
        weights=weights,
        algorithm="duration-lpt-v1",
        status="exact" if exact else "compatible",
        reason="profile-exact" if exact else "product-source-drift",
        requested=requested,
        profile_digest=hashlib.sha256(raw).hexdigest(),
        profile_path=PROFILE_RELATIVE_PATH.as_posix(),
        source_run_ids=tuple(source["evidence_run_ids"]),
    )


def _partition_assignment_digest(shards: Sequence[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for shard in sorted(shards, key=lambda item: int(item["index"])):
        digest.update(int(shard["index"]).to_bytes(4, "big"))
        for path in shard["test_files"]:
            encoded = str(path).encode("utf-8")
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
    return digest.hexdigest()


def _validated_partition(
    value: object,
    *,
    shard_count: int,
) -> tuple[dict[str, Any], dict[str, int]]:
    partition = _exact_mapping(value, _PARTITION_KEYS, label="timing partition")
    for key in ("algorithm", "reason", "requested", "status"):
        text = partition[key]
        if (
            not isinstance(text, str)
            or not 1 <= len(text) <= 64
            or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", text)
        ):
            raise ValueError("timing partition state is invalid")
    profile_digest = partition["profile_digest"]
    profile_path = partition["profile_path"]
    if profile_digest is not None and (
        not isinstance(profile_digest, str) or not _HEX_64.fullmatch(profile_digest)
    ):
        raise ValueError("timing partition profile digest is invalid")
    if profile_path is not None and profile_path != PROFILE_RELATIVE_PATH.as_posix():
        raise ValueError("timing partition profile path is invalid")
    source_run_ids = partition["source_run_ids"]
    if (
        not isinstance(source_run_ids, list)
        or len(source_run_ids) > MAX_PROFILE_SAMPLES
        or any(
            not isinstance(run_id, str) or not _HEX_32.fullmatch(run_id)
            for run_id in source_run_ids
        )
    ):
        raise ValueError("timing partition source runs are invalid")
    raw_shards = partition["shards"]
    if not isinstance(raw_shards, list) or len(raw_shards) != shard_count:
        raise ValueError("timing partition shards are invalid")
    assignments: dict[str, int] = {}
    casefolded: set[str] = set()
    validated_shards: list[dict[str, Any]] = []
    for raw_shard in raw_shards:
        shard = _exact_mapping(
            raw_shard,
            {"index", "test_files", "weight_total"},
            label="timing partition shard",
        )
        index = _nonnegative_integer(
            shard["index"],
            label="timing partition shard index",
            maximum=MAX_PROFILE_FILES - 1,
        )
        paths = shard["test_files"]
        if not isinstance(paths, list) or not paths:
            raise ValueError("timing partition shard file list is invalid")
        canonical_paths = []
        for value_path in paths:
            path = _canonical_repository_test_path(value_path)
            folded = path.casefold()
            if path in assignments or folded in casefolded:
                raise ValueError("timing partition contains duplicate paths")
            assignments[path] = index
            casefolded.add(folded)
            canonical_paths.append(path)
        if canonical_paths != sorted(canonical_paths):
            raise ValueError("timing partition shard paths are not canonical order")
        validated_shards.append(
            {
                "index": index,
                "test_files": canonical_paths,
                "weight_total": _positive_integer(
                    shard["weight_total"],
                    label="timing partition shard weight",
                    maximum=MAX_WEIGHT_NS,
                ),
            }
        )
    if {item["index"] for item in validated_shards} != set(range(shard_count)):
        raise ValueError("timing partition shard indexes are invalid")
    if validated_shards != sorted(validated_shards, key=lambda item: item["index"]):
        raise ValueError("timing partition shards are not canonical order")
    assignment_digest = partition["assignment_sha256"]
    if (
        not isinstance(assignment_digest, str)
        or not _HEX_64.fullmatch(assignment_digest)
        or assignment_digest != _partition_assignment_digest(validated_shards)
    ):
        raise ValueError("timing partition assignment digest is invalid")
    return partition, assignments


def _validated_measurement_context(value: object) -> dict[str, Any]:
    context = _exact_mapping(value, _MEASUREMENT_KEYS, label="timing measurement context")
    for key in (
        "content_set_sha256",
        "harness_sha256",
        "path_set_sha256",
        "product_source_sha256",
        "runtime_key",
    ):
        if not isinstance(context[key], str) or not _HEX_64.fullmatch(context[key]):
            raise ValueError("timing measurement digest is invalid")
    commit = context["repository_commit"]
    if commit is not None and (not isinstance(commit, str) or not _HEX_40.fullmatch(commit)):
        raise ValueError("timing repository commit is invalid")
    if not isinstance(context["relevant_tree_clean"], bool):
        raise ValueError("timing repository cleanliness is invalid")
    for key in (
        "architecture",
        "corpus",
        "metric",
        "platform",
        "pytest_version",
        "python_implementation",
        "python_minor",
        "test_root",
    ):
        text = context[key]
        if (
            not isinstance(text, str)
            or not 1 <= len(text) <= 512
            or any(ord(character) < 32 for character in text)
        ):
            raise ValueError("timing measurement identity is invalid")
    _positive_integer(
        context["worker_count"],
        label="timing worker count",
        maximum=MAX_PROFILE_FILES,
    )
    if context["runtime_contract_version"] != RUNTIME_CONTRACT_VERSION:
        raise ValueError("timing runtime contract version is unsupported")
    return context


def _phase_integers(value: object, *, label: str, maximum: int) -> dict[str, int]:
    phases = _exact_mapping(value, {"call", "setup", "teardown"}, label=label)
    return {
        phase: _nonnegative_integer(
            phases[phase],
            label=f"{label} {phase}",
            maximum=maximum,
        )
        for phase in ("setup", "call", "teardown")
    }


def _validated_timing_files(
    value: object,
    *,
    file_count: int,
    assignments: Mapping[str, int],
) -> tuple[dict[str, int], dict[int, tuple[int, int]]]:
    if not isinstance(value, list) or len(value) != file_count:
        raise ValueError("timing artifact file records are invalid")
    weights: dict[str, int] = {}
    shard_totals: dict[int, list[int]] = {}
    ordered_paths: list[str] = []
    casefolded: set[str] = set()
    for raw_item in value:
        item = _exact_mapping(
            raw_item,
            {
                "collected_items",
                "duration_ns",
                "path",
                "report_counts",
                "shard",
                "total_ns",
            },
            label="timing file record",
        )
        path = _canonical_profile_path(item["path"])
        folded = path.casefold()
        if path in weights or folded in casefolded or path not in assignments:
            raise ValueError("timing artifact contains an invalid file path")
        shard = _nonnegative_integer(
            item["shard"],
            label="timing file shard",
            maximum=MAX_PROFILE_FILES - 1,
        )
        if assignments[path] != shard:
            raise ValueError("timing file is assigned to the wrong shard")
        collected = _nonnegative_integer(
            item["collected_items"],
            label="timing collected items",
            maximum=1_000_000,
        )
        durations = _phase_integers(
            item["duration_ns"],
            label="timing phase duration",
            maximum=MAX_WEIGHT_NS,
        )
        counts = _phase_integers(
            item["report_counts"],
            label="timing phase count",
            maximum=1_000_000,
        )
        if any(count > collected for count in counts.values()):
            raise ValueError("timing phase count exceeds collected items")
        total_ns = _positive_integer(
            item["total_ns"],
            label="timing file duration",
            maximum=MAX_WEIGHT_NS,
        )
        if sum(durations.values()) != total_ns:
            raise ValueError("timing file duration total is inconsistent")
        weights[path] = total_ns
        ordered_paths.append(path)
        casefolded.add(folded)
        totals = shard_totals.setdefault(shard, [0, 0])
        totals[0] += collected
        totals[1] += sum(counts.values())
    if ordered_paths != sorted(ordered_paths) or set(weights) != set(assignments):
        raise ValueError("timing artifact file union is invalid")
    return weights, {index: tuple(values) for index, values in shard_totals.items()}


def _validate_timing_shards(
    value: object,
    *,
    shard_count: int,
    shard_totals: Mapping[int, tuple[int, int]],
) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != shard_count:
        raise ValueError("timing artifact shards are invalid")
    collected_total = 0
    phase_total = 0
    indexes: list[int] = []
    for raw_item in value:
        item = _exact_mapping(
            raw_item,
            {"collected_item_count", "exit_status", "index", "phase_report_count"},
            label="timing shard record",
        )
        index = _nonnegative_integer(
            item["index"],
            label="timing shard index",
            maximum=MAX_PROFILE_FILES - 1,
        )
        collected = _nonnegative_integer(
            item["collected_item_count"],
            label="timing shard collected count",
            maximum=1_000_000,
        )
        phases = _nonnegative_integer(
            item["phase_report_count"],
            label="timing shard phase count",
            maximum=3_000_000,
        )
        if item["exit_status"] != 0 or shard_totals.get(index) != (collected, phases):
            raise ValueError("timing artifact shard totals are inconsistent")
        indexes.append(index)
        collected_total += collected
        phase_total += phases
    if indexes != list(range(shard_count)):
        raise ValueError("timing artifact shard indexes are invalid")
    return collected_total, phase_total


def _validated_timing_artifact(raw: bytes) -> tuple[dict[str, Any], dict[str, int]]:
    payload = safe_load_bounded_json(
        raw,
        maximum_bytes=MAX_RUN_TIMING_BYTES,
        maximum_depth=8,
        maximum_nodes=MAX_PROFILE_FILES * 16,
    )
    root = _exact_mapping(
        payload,
        {
            "collected_item_count",
            "files",
            "measurement_context",
            "partition",
            "phase_report_count",
            "run_id",
            "schema",
            "shard_count",
            "shards",
            "test_file_count",
        },
        label="timing artifact",
    )
    if (
        root["schema"] != RUN_TIMING_SCHEMA
        or not isinstance(root["run_id"], str)
        or not _HEX_32.fullmatch(root["run_id"])
    ):
        raise ValueError("timing artifact identity is invalid")
    context = _validated_measurement_context(root["measurement_context"])
    file_count = _positive_integer(
        root["test_file_count"],
        label="timing file count",
        maximum=MAX_PROFILE_FILES,
    )
    shard_count = _positive_integer(
        root["shard_count"],
        label="timing shard count",
        maximum=MAX_PROFILE_FILES,
    )
    if context["worker_count"] != shard_count or context["test_root"] != "tests":
        raise ValueError("timing artifact context does not match its shard contract")
    _partition, assignments = _validated_partition(root["partition"], shard_count=shard_count)
    if len(assignments) != file_count:
        raise ValueError("timing partition file count is inconsistent")
    weights, shard_totals = _validated_timing_files(
        root["files"],
        file_count=file_count,
        assignments=assignments,
    )
    collected_total, phase_total = _validate_timing_shards(
        root["shards"],
        shard_count=shard_count,
        shard_totals=shard_totals,
    )
    if (
        _nonnegative_integer(
            root["collected_item_count"],
            label="timing collected total",
            maximum=1_000_000,
        )
        != collected_total
        or _nonnegative_integer(
            root["phase_report_count"],
            label="timing phase total",
            maximum=3_000_000,
        )
        != phase_total
    ):
        raise ValueError("timing artifact aggregate totals are inconsistent")
    return root, weights


def _expected_source_byte_partition(
    repo_root: Path,
    test_files: Sequence[Path],
    *,
    worker_count: int,
) -> dict[str, Any]:
    weights = {path: max(1, path.stat().st_size) for path in test_files}
    selected = partition_test_files(
        test_files,
        shard_count=worker_count,
        weights=weights,
    )
    shards = [
        {
            "index": index,
            "test_files": [path.relative_to(repo_root).as_posix() for path in shard],
            "weight_total": sum(weights[path] for path in shard),
        }
        for index, shard in enumerate(selected)
    ]
    return {
        "algorithm": "source-bytes-lpt-v1",
        "assignment_sha256": _partition_assignment_digest(shards),
        "profile_digest": None,
        "profile_path": None,
        "reason": "explicit-source-bytes",
        "requested": "source-bytes",
        "shards": shards,
        "source_run_ids": [],
        "status": "disabled",
    }


def build_weight_profile(
    repo_root: Path,
    timing_artifacts: Sequence[Path],
    *,
    evidence_commit: str,
    worker_count: int,
    pytest_flags: Sequence[str],
) -> dict[str, Any]:
    """Build one deterministic median profile from source-equivalent green runs."""

    if not _HEX_40.fullmatch(evidence_commit):
        raise ValueError("evidence_commit must be a full Git SHA")
    if (
        not MIN_PROFILE_SAMPLES <= len(timing_artifacts) <= MAX_PROFILE_SAMPLES
        or len(timing_artifacts) % 2 == 0
    ):
        raise ValueError("timing profile requires an odd production sample")
    repo = repo_root.resolve(strict=True)
    test_files = discover_test_files(repo / "tests")
    current_paths, current_digests, current_sizes = _test_inventory(repo, test_files)
    parsed: list[tuple[dict[str, Any], dict[str, int], str]] = []
    for path in timing_artifacts:
        raw = read_bounded_regular_file(
            path,
            limit=MAX_RUN_TIMING_BYTES,
            label="pytest timing artifact",
        )
        root, weights = _validated_timing_artifact(raw)
        parsed.append((root, weights, hashlib.sha256(raw).hexdigest()))
    parsed.sort(key=lambda item: item[0]["run_id"])
    contexts = [item[0]["measurement_context"] for item in parsed]
    first_context = contexts[0]
    if any(context != first_context for context in contexts[1:]):
        raise ValueError("timing artifacts do not share one measurement context")
    if (
        first_context["repository_commit"] != evidence_commit
        or first_context["relevant_tree_clean"] is not True
    ):
        raise ValueError("timing artifacts are not clean evidence for the requested commit")
    expected_context = build_measurement_context(
        repo,
        test_files,
        worker_count=worker_count,
        pytest_flags=pytest_flags,
        runtime_key=first_context["runtime_key"],
    )
    if first_context != expected_context:
        raise ValueError("timing artifacts are stale for the current source and harness")
    expected_partition = _expected_source_byte_partition(
        repo,
        test_files,
        worker_count=worker_count,
    )
    if any(root["partition"] != expected_partition for root, _weights, _digest in parsed):
        raise ValueError("timing artifacts do not use the exact source-byte control partition")
    if any(set(weights) != set(current_paths) for _root, weights, _digest in parsed):
        raise ValueError("timing artifacts differ from the current test union")
    run_ids = [item[0]["run_id"] for item in parsed]
    if len(set(run_ids)) != len(run_ids):
        raise ValueError("timing artifact run identities are duplicated")
    records = []
    for path in sorted(current_paths):
        samples = [weights[path] for _root, weights, _digest in parsed]
        median = statistics.median(samples)
        if not isinstance(median, int) or not math.isfinite(float(median)):
            raise ValueError("timing profile median is not an exact integer")
        records.append(
            {
                "path": path,
                "source_bytes": current_sizes[path],
                "source_sha256": current_digests[path],
                "weight_ns": median,
            }
        )
    return {
        "files": records,
        "profile": {
            "aggregation": AGGREGATION_ID,
            "architecture": first_context["architecture"],
            "corpus": first_context["corpus"],
            "metric": first_context["metric"],
            "platform": first_context["platform"],
            "pytest_version": first_context["pytest_version"],
            "python_implementation": first_context["python_implementation"],
            "python_minor": first_context["python_minor"],
            "runtime_contract_version": first_context["runtime_contract_version"],
            "sample_count": len(parsed),
            "worker_count": first_context["worker_count"],
        },
        "schema": PROFILE_SCHEMA,
        "source": {
            "content_set_sha256": first_context["content_set_sha256"],
            "evidence_artifact_sha256": [item[2] for item in parsed],
            "evidence_commit": evidence_commit,
            "evidence_run_ids": run_ids,
            "evidence_runtime_keys": [context["runtime_key"] for context in contexts],
            "harness_sha256": first_context["harness_sha256"],
            "path_set_sha256": first_context["path_set_sha256"],
            "product_source_sha256": first_context["product_source_sha256"],
            "test_file_count": len(records),
            "test_root": "tests",
        },
    }


def write_weight_profile(repo_root: Path, payload: Mapping[str, Any]) -> Path:
    """Atomically write the fixed repository-owned Windows profile path."""

    repo = repo_root.resolve(strict=True)
    target = repo / PROFILE_RELATIVE_PATH
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink() or parent.resolve(strict=True) != parent:
        raise RuntimeError("pytest shard weight directory is not canonical")
    if target.exists() and target.is_symlink():
        raise RuntimeError("pytest shard weight profile must not be a link")
    encoded = (
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True).encode("ascii") + b"\n"
    )
    if len(encoded) > MAX_PROFILE_BYTES:
        raise ValueError("pytest shard weight profile exceeds its byte bound")
    descriptor, temporary_value = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=parent,
    )
    temporary = Path(temporary_value)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            os.chmod(temporary, 0o644)
        os.replace(temporary, target)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--evidence-commit", required=True)
    parser.add_argument("--timing-artifact", type=Path, action="append", required=True)
    args = parser.parse_args(argv)
    from scripts.run_parallel_change_loop import DEFAULT_SHARD_COUNT, PYTEST_FLAGS

    payload = build_weight_profile(
        args.repo_root,
        args.timing_artifact,
        evidence_commit=args.evidence_commit,
        worker_count=DEFAULT_SHARD_COUNT,
        pytest_flags=PYTEST_FLAGS,
    )
    output = write_weight_profile(args.repo_root, payload)
    print(output.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CORPUS_ID",
    "MAX_PROFILE_BYTES",
    "METRIC_ID",
    "PROFILE_RELATIVE_PATH",
    "PROFILE_SCHEMA",
    "PartitionWeights",
    "build_measurement_context",
    "build_weight_profile",
    "load_partition_weights",
    "write_weight_profile",
]
