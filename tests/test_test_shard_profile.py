from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.pytest_file_timing import RUN_TIMING_SCHEMA
from scripts.select_test_shard import discover_test_files, partition_test_files
from scripts.test_shard_profile import (
    PROFILE_RELATIVE_PATH,
    build_measurement_context,
    build_weight_profile,
    load_partition_weights,
    write_weight_profile,
)

_FLAGS = ("-q", "-W", "error", "-p", "no:cacheprovider", "-m", "not performance")
_RUNTIME_KEY = "a" * 64


def _repository(tmp_path: Path) -> tuple[Path, tuple[Path, ...]]:
    repository = tmp_path / "repo"
    tests = repository / "tests"
    tests.mkdir(parents=True)
    product = repository / "agency_runtime"
    product.mkdir()
    (product / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    for index, size in enumerate((11, 13, 17, 19)):
        (tests / f"test_{index}.py").write_text("x" * size, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "tests@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.name", "Agency Tests"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "add", "agency_runtime", "tests"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-q", "-m", "test fixture"],
        check=True,
    )
    return repository, discover_test_files(tests)


def _artifact(
    context: dict[str, object],
    files: tuple[Path, ...],
    *,
    run_id: str,
    durations: tuple[int, ...],
) -> bytes:
    repository = files[0].parents[1]
    weights = {path: max(1, path.stat().st_size) for path in files}
    selected = partition_test_files(files, shard_count=4, weights=weights)
    assignments = {path: index for index, shard in enumerate(selected) for path in shard}
    records = [
        {
            "collected_items": 1,
            "duration_ns": {"call": duration, "setup": 0, "teardown": 0},
            "path": path.parent.name + "/" + path.name,
            "report_counts": {"call": 1, "setup": 1, "teardown": 1},
            "shard": assignments[path],
            "total_ns": duration,
        }
        for path, duration in zip(files, durations, strict=True)
    ]
    partition_shards = [
        {
            "index": index,
            "test_files": [path.relative_to(repository).as_posix() for path in shard],
            "weight_total": sum(weights[path] for path in shard),
        }
        for index, shard in enumerate(selected)
    ]
    assignment_digest = hashlib.sha256()
    for shard in partition_shards:
        assignment_digest.update(shard["index"].to_bytes(4, "big"))
        for path in shard["test_files"]:
            encoded = path.encode("utf-8")
            assignment_digest.update(len(encoded).to_bytes(8, "big"))
            assignment_digest.update(encoded)
    return (
        json.dumps(
            {
                "collected_item_count": len(files),
                "files": records,
                "measurement_context": context,
                "partition": {
                    "algorithm": "source-bytes-lpt-v1",
                    "assignment_sha256": assignment_digest.hexdigest(),
                    "profile_digest": None,
                    "profile_path": None,
                    "reason": "explicit-source-bytes",
                    "requested": "source-bytes",
                    "shards": partition_shards,
                    "source_run_ids": [],
                    "status": "disabled",
                },
                "phase_report_count": len(files) * 3,
                "run_id": run_id,
                "schema": RUN_TIMING_SCHEMA,
                "shard_count": 4,
                "shards": [
                    {
                        "collected_item_count": 1,
                        "exit_status": 0,
                        "index": index,
                        "phase_report_count": 3,
                    }
                    for index in range(4)
                ],
                "test_file_count": len(files),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        + b"\n"
    )


def _timing_inputs(
    repository: Path,
    files: tuple[Path, ...],
) -> tuple[dict[str, object], tuple[Path, ...]]:
    context = build_measurement_context(
        repository,
        files,
        worker_count=4,
        pytest_flags=_FLAGS,
        runtime_key=_RUNTIME_KEY,
    )
    paths = []
    samples = (
        (40, 30, 20, 10),
        (44, 32, 18, 12),
        (42, 28, 22, 8),
    )
    for index, durations in enumerate(samples, start=1):
        path = repository / f"timing-{index}.json"
        path.write_bytes(
            _artifact(
                context,
                files,
                run_id=f"{index:032x}",
                durations=durations,
            )
        )
        paths.append(path)
    return context, tuple(paths)


def _install_profile(
    repository: Path,
    files: tuple[Path, ...],
) -> tuple[dict[str, object], tuple[Path, ...]]:
    context, paths = _timing_inputs(repository, files)
    payload = build_weight_profile(
        repository,
        paths,
        evidence_commit=str(context["repository_commit"]),
        worker_count=4,
        pytest_flags=_FLAGS,
    )
    write_weight_profile(repository, payload)
    return payload, paths


def _load(repository: Path, files: tuple[Path, ...], **overrides: object):
    arguments = {
        "worker_count": 4,
        "pytest_flags": _FLAGS,
        "runtime_key": _RUNTIME_KEY,
    }
    arguments.update(overrides)
    return load_partition_weights(repository, files, **arguments)  # type: ignore[arg-type]


def test_exact_profile_is_deterministic_and_drives_duration_lpt(tmp_path: Path) -> None:
    repository, files = _repository(tmp_path)
    first_payload, artifacts = _install_profile(repository, files)
    (repository / PROFILE_RELATIVE_PATH).unlink()
    second_payload = build_weight_profile(
        repository,
        tuple(reversed(artifacts)),
        evidence_commit=str(first_payload["source"]["evidence_commit"]),
        worker_count=4,
        pytest_flags=_FLAGS,
    )
    write_weight_profile(repository, second_payload)

    assert first_payload == second_payload
    selected = _load(repository, files)
    assert selected.status == "exact"
    assert selected.algorithm == "duration-lpt-v1"
    assert selected.source_run_ids == tuple(f"{index:032x}" for index in range(1, 4))
    assert [selected.weights[path] for path in files] == [42, 30, 20, 10]
    shards = partition_test_files(files, shard_count=2, weights=selected.weights)
    assert {path for shard in shards for path in shard} == set(files)
    assert [sum(selected.weights[path] for path in shard) for shard in shards] == [52, 50]


def test_profile_mtime_change_stays_exact_but_same_size_content_change_is_stale(
    tmp_path: Path,
) -> None:
    repository, files = _repository(tmp_path)
    _install_profile(repository, files)
    metadata = files[0].stat()
    os.utime(files[0], ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 1_000_000))
    assert _load(repository, files).status == "exact"

    files[0].write_text("y" * metadata.st_size, encoding="utf-8")
    stale = _load(repository, files)
    assert stale.status == "stale"
    assert stale.algorithm == "source-bytes-lpt-v1"
    with pytest.raises(RuntimeError, match="stale"):
        _load(repository, files, require_exact=True)


@pytest.mark.parametrize("mutation", ["added", "deleted", "renamed", "harness"])
def test_inventory_and_harness_changes_fall_back_for_the_whole_corpus(
    tmp_path: Path,
    mutation: str,
) -> None:
    repository, files = _repository(tmp_path)
    _install_profile(repository, files)
    if mutation == "added":
        (repository / "tests" / "test_added.py").write_text("pass\n", encoding="utf-8")
    elif mutation == "deleted":
        files[0].unlink()
    elif mutation == "renamed":
        files[0].rename(files[0].with_name("test_renamed.py"))
    else:
        (repository / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", "utf-8")
    current = discover_test_files(repository / "tests")

    selection = _load(repository, current)

    assert selection.status == "stale"
    assert selection.algorithm == "source-bytes-lpt-v1"
    assert set(selection.weights) == set(current)


def test_missing_invalid_unsupported_and_strict_profile_states_are_bounded(
    tmp_path: Path,
) -> None:
    repository, files = _repository(tmp_path)
    missing = _load(repository, files)
    assert (missing.status, missing.reason) == ("missing", "profile-missing")
    with pytest.raises(RuntimeError, match="missing"):
        _load(repository, files, require_exact=True)

    target = repository / PROFILE_RELATIVE_PATH
    target.parent.mkdir(parents=True)
    target.write_text('{"schema":"bad","schema":"duplicate"}', encoding="utf-8")
    invalid = _load(repository, files)
    assert (invalid.status, invalid.reason) == ("invalid", "profile-invalid")
    with pytest.raises(RuntimeError, match="invalid"):
        _load(repository, files, require_exact=True)

    unsupported = _load(
        repository,
        files,
        platform_name="linux",
        python_implementation="CPython",
    )
    assert (unsupported.status, unsupported.reason) == (
        "unsupported",
        "unsupported-runtime",
    )


def test_runtime_identity_and_worker_count_mismatch_are_stale(tmp_path: Path) -> None:
    repository, files = _repository(tmp_path)
    _install_profile(repository, files)

    assert _load(repository, files, architecture="arm64").status == "stale"
    assert _load(repository, files, python_minor="3.14").status == "stale"
    assert _load(repository, files, pytest_version="10.0.0").status == "stale"
    assert _load(repository, files, worker_count=3).status == "stale"


def test_product_source_drift_uses_compatible_weights_but_strict_mode_rejects(
    tmp_path: Path,
) -> None:
    repository, files = _repository(tmp_path)
    _install_profile(repository, files)
    (repository / "agency_runtime" / "__init__.py").write_text("VALUE = 2\n", encoding="utf-8")

    compatible = _load(repository, files)

    assert (compatible.status, compatible.reason) == (
        "compatible",
        "product-source-drift",
    )
    assert compatible.algorithm == "duration-lpt-v1"
    with pytest.raises(RuntimeError, match="stale"):
        _load(repository, files, require_exact=True)


def test_generator_rejects_wrong_commit_and_dirty_current_tree(tmp_path: Path) -> None:
    repository, files = _repository(tmp_path)
    context, artifacts = _timing_inputs(repository, files)

    with pytest.raises(ValueError, match="clean evidence"):
        build_weight_profile(
            repository,
            artifacts,
            evidence_commit="f" * 40,
            worker_count=4,
            pytest_flags=_FLAGS,
        )

    extra = repository / "scripts" / "untracked.py"
    extra.parent.mkdir()
    extra.write_text("pass\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        build_weight_profile(
            repository,
            artifacts,
            evidence_commit=str(context["repository_commit"]),
            worker_count=4,
            pytest_flags=_FLAGS,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("algorithm", "duration-lpt-v1", "source-byte control"),
        ("weight_total", 999, "source-byte control"),
        ("collected_item_count", 999, "aggregate totals"),
        ("run_id", 1, "identity"),
    ],
)
def test_generator_rejects_forged_partition_and_aggregate_evidence(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    repository, files = _repository(tmp_path)
    context, artifacts = _timing_inputs(repository, files)
    payload = json.loads(artifacts[0].read_text("utf-8"))
    if field == "weight_total":
        payload["partition"]["shards"][0][field] = value
    elif field in payload["partition"]:
        payload["partition"][field] = value
    else:
        payload[field] = value
    artifacts[0].write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        build_weight_profile(
            repository,
            artifacts,
            evidence_commit=str(context["repository_commit"]),
            worker_count=4,
            pytest_flags=_FLAGS,
        )


def test_generator_rejects_linked_timing_artifact(tmp_path: Path) -> None:
    repository, files = _repository(tmp_path)
    context, artifacts = _timing_inputs(repository, files)
    link = repository / "timing-link.json"
    try:
        link.symlink_to(artifacts[0])
    except OSError:
        pytest.skip("the test host cannot create a file symlink")

    with pytest.raises(OSError, match="non-link"):
        build_weight_profile(
            repository,
            (link, *artifacts[1:]),
            evidence_commit=str(context["repository_commit"]),
            worker_count=4,
            pytest_flags=_FLAGS,
        )


def test_explicit_source_bytes_never_reads_the_profile(tmp_path: Path) -> None:
    repository, files = _repository(tmp_path)
    target = repository / PROFILE_RELATIVE_PATH
    target.parent.mkdir(parents=True)
    target.write_text("not json", encoding="utf-8")

    selection = _load(repository, files, strategy="source-bytes")

    assert (selection.status, selection.reason) == (
        "disabled",
        "explicit-source-bytes",
    )
    with pytest.raises(ValueError, match="automatic"):
        _load(repository, files, strategy="source-bytes", require_exact=True)
