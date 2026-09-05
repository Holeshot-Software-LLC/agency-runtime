"""Cross-process recall reuse must preserve vectors, scope and trust."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace

import pytest

from agency_runtime.core.workforce.embedding_provider import EmbeddingProviderResponse
from agency_runtime.core.workforce.hybrid_recall import (
    clear_hybrid_recall_cache,
    discover_hybrid_recall,
)
from tests.test_workforce_hybrid_recall import _contract, _plan


def _discover(directory, *, identity="catalog-a", model="actual-v1", changed=False):
    calls = []
    contracts = (
        _contract("baseline-primary", outcome="Existing primary baseline"),
        _contract("dense-primary", outcome="Novel primary semantic expertise"),
    )
    if changed:
        contracts = (contracts[0], replace(contracts[1], outcomes=("Changed expertise",)))

    def invoke(texts):
        calls.append(len(texts))
        return EmbeddingProviderResponse(
            tuple((0.6, 0.8) for _ in texts),
            provider_name="fixture-provider",
            requested_model="fixture-model",
            actual_model=model,
        )

    result = discover_hybrid_recall(
        _plan(),
        contracts,
        typed_candidate_ids={"unit-primary": ("baseline-primary",)},
        catalog_identity=identity,
        provider_name="fixture-provider",
        requested_model="fixture-model",
        embedding_invoker=invoke,
        catalog_cache_directory=directory,
    )
    return result, calls


def test_fresh_process_reuses_roster_vectors_but_embeds_every_new_query(tmp_path):
    program = (
        "import json,sys; from pathlib import Path; "
        "from tests.test_persistent_hybrid_recall_cache import _discover; "
        "r,c=_discover(Path(sys.argv[1])); "
        "print(json.dumps({'calls':c,'hit':r.receipt.catalog_cache_hit,"
        "'units':repr(r.units)}))"
    )
    directory = tmp_path / "vectors"
    results = [
        json.loads(
            subprocess.run(
                [sys.executable, "-c", program, str(directory)],
                capture_output=True,
                text=True,
                check=True,
                timeout=20,
            ).stdout
        )
        for _ in range(2)
    ]
    assert [row["calls"] for row in results] == [[3], [1]]
    assert [row["hit"] for row in results] == [False, True]
    assert results[0]["units"] == results[1]["units"]
    payload = next(directory.glob("*.json")).read_text()
    assert "Assess" not in payload
    assert "primary" not in payload
    if os.name != "nt":
        assert directory.stat().st_mode & 0o777 == 0o700
        assert next(directory.glob("*.json")).stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("change", ["identity", "roster", "directory", "expired", "corrupt"])
def test_invalidations_rebuild_without_reusing_wrong_vectors(tmp_path, monkeypatch, change):
    from agency_runtime.core.workforce import catalog_vector_cache

    directory = tmp_path / "vectors"
    _discover(directory)
    clear_hybrid_recall_cache()
    options = {}
    if change == "identity":
        options["identity"] = "catalog-b"
    elif change == "roster":
        options["changed"] = True
    elif change == "directory":
        directory = tmp_path / "other"
    elif change == "expired":
        now = catalog_vector_cache.time.time()
        monkeypatch.setattr(catalog_vector_cache.time, "time", lambda: now + 3601)
    else:
        next(directory.glob("*.json")).write_text("{}")
    result, calls = _discover(directory, **options)
    assert calls == [3]
    assert result.receipt.catalog_cache_hit is False
    assert result.receipt.status == "applied"


def test_actual_model_change_evicts_disk_entry_and_never_mixes_vector_spaces(tmp_path):
    directory = tmp_path / "vectors"
    _discover(directory)
    clear_hybrid_recall_cache()
    mismatch, calls = _discover(directory, model="actual-v2")
    assert calls == [1]
    assert mismatch.receipt.reason_code == "embedding_model_mismatch"
    assert all(not unit.additions for unit in mismatch.units)
    clear_hybrid_recall_cache()
    rebuilt, calls = _discover(directory, model="actual-v2")
    assert calls == [3]
    assert rebuilt.receipt.status == "applied"


def test_failure_receipt_keeps_bounded_recall_work_counts_not_inputs():
    from agency_runtime.core.preflight_failure import project_preflight_provider_attempts
    from tests.test_preflight_failure_diagnosis import _attempt

    [row] = project_preflight_provider_attempts(
        [
            _attempt(
                stage="recall_embedding",
                input_count=294,
                provider_call_count=1,
                catalog_cache_hit=False,
                query="private",
                vectors=[1, 0],
            )
        ]
    )
    assert row["input_count"] == 294
    assert row["provider_call_count"] == 1
    assert row["catalog_cache_hit"] is False
    assert "query" not in row and "vectors" not in row
    [invalid] = project_preflight_provider_attempts(
        [
            _attempt(
                stage="recall_embedding",
                input_count=True,
                provider_call_count=100,
                catalog_cache_hit="private",
            )
        ]
    )
    assert not {"input_count", "provider_call_count", "catalog_cache_hit"} & invalid.keys()


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission/link boundary")
@pytest.mark.parametrize("kind", ["directory-link", "file-link", "hard-link", "public"])
def test_unsafe_cache_is_ignored_without_touching_target(tmp_path, kind):
    directory = tmp_path / "vectors"
    _discover(directory)
    clear_hybrid_recall_cache()
    slot = next(directory.glob("*.json"))
    target = tmp_path / "unrelated"
    original = slot.read_bytes()
    if kind == "directory-link":
        actual = directory.rename(tmp_path / "actual")
        directory.symlink_to(actual, target_is_directory=True)
        target = actual / slot.name
    elif kind == "public":
        directory.chmod(0o777)
        target = slot
    else:
        slot.rename(target)
        if kind == "file-link":
            slot.symlink_to(target)
        else:
            os.link(target, slot)
    result, calls = _discover(directory)
    assert calls == [3]
    assert result.receipt.status == "applied"
    assert target.read_bytes() == original
