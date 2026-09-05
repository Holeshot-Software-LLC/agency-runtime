"""Disposable owner-private roster vectors shared by fresh hook processes.

Only positive roster document vectors are stored: never queries, prompts or
staffing decisions. Two fixed slots bound disk use without directory scanning.
Lossless float64 encoding preserves the existing normalized recall ranking.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import stat
import sys
import time
from array import array
from dataclasses import dataclass, field
from pathlib import Path

from agency_runtime.core.bounded_io import atomic_write_text, read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.configuration import restrict_private_file
from agency_runtime.core.private_paths import ensure_private_directory, validate_private_directory
from agency_runtime.core.roster.limits import MAX_ACTIVE_ROSTER_SIZE
from agency_runtime.core.store.security import storage_file_is_trusted
from agency_runtime.core.workforce.embedding_provider import (
    MAX_EMBEDDING_DIMENSIONS,
    MAX_EMBEDDING_VECTOR_VALUES,
)

CATALOG_VECTOR_TTL_SECONDS = 3600
MAX_CATALOG_CACHE_BYTES = 24 * 1024 * 1024
MAX_CATALOG_VECTOR_VALUES = 2 * MAX_EMBEDDING_VECTOR_VALUES
CatalogCacheKey = tuple[str, str, str, str]


@dataclass(frozen=True, slots=True)
class CatalogVectorEntry:
    catalog_fingerprint: str
    document_vectors: tuple[tuple[float, ...], ...]
    provider_name: str
    requested_model: str
    actual_model: str
    dimensions: int
    created_at: float = field(default_factory=lambda: time.time())


def entry_is_fresh(entry: CatalogVectorEntry) -> bool:
    return (
        math.isfinite(entry.created_at)
        and 0 <= time.time() - entry.created_at < CATALOG_VECTOR_TTL_SECONDS
    )


def _slot(directory: Path, key: CatalogCacheKey) -> Path:
    digest = hashlib.sha256(json.dumps(key).encode()).digest()
    return directory / f"catalog-{digest[0] % 2}.json"


def _trusted_file(path: Path) -> bool:
    if not storage_file_is_trusted(path, is_windows=os.name == "nt"):
        return False
    return os.name == "nt" or not stat.S_IMODE(path.lstat().st_mode) & 0o077


def _read(directory: Path, key: CatalogCacheKey) -> dict:
    validate_private_directory(directory)
    path = _slot(directory, key)
    if not _trusted_file(path):
        raise ValueError("untrusted catalog cache")
    payload = read_bounded_regular_file(path, limit=MAX_CATALOG_CACHE_BYTES)
    value = safe_load_bounded_json(
        payload, maximum_bytes=MAX_CATALOG_CACHE_BYTES, maximum_depth=4, maximum_nodes=64
    )
    if not isinstance(value, dict) or value.get("key") != list(key) or value.get("version") != 1:
        raise ValueError("catalog cache identity mismatch")
    return value


def _vectors(encoded: str, *, count: int, dimensions: int) -> tuple[tuple[float, ...], ...]:
    if (
        isinstance(dimensions, bool)
        or not isinstance(dimensions, int)
        or not 1 <= dimensions <= MAX_EMBEDDING_DIMENSIONS
        or not 1 <= count <= MAX_ACTIVE_ROSTER_SIZE
        or count * dimensions > MAX_CATALOG_VECTOR_VALUES
    ):
        raise ValueError("catalog matrix bounds")
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) != count * dimensions * 8:
        raise ValueError("catalog matrix size mismatch")
    values = array("d")
    if values.itemsize != 8:
        raise ValueError("catalog float representation unavailable")
    values.frombytes(raw)
    if sys.byteorder != "little":
        values.byteswap()
    rows = tuple(
        tuple(values[offset : offset + dimensions]) for offset in range(0, len(values), dimensions)
    )
    # Reject tampering/corruption without re-normalizing (which could perturb
    # a tied ranking). These are the exact already-normalized float64 values.
    for row in rows:
        if not all(math.isfinite(value) and abs(value) <= 1 for value in row):
            raise ValueError("catalog matrix is nonfinite or unbounded")
        if not math.isclose(math.fsum(value * value for value in row), 1, abs_tol=1e-9):
            raise ValueError("catalog matrix is not normalized")
    return rows


def load_catalog_vectors(
    directory: Path | None,
    key: CatalogCacheKey,
    *,
    fingerprint: str,
    count: int,
) -> CatalogVectorEntry | None:
    if directory is None:
        return None
    try:
        value = _read(directory, key)
        if value.get("fingerprint") != fingerprint:
            return None
        if any(
            not isinstance(value.get(name), str) or not 1 <= len(value[name]) <= 512
            for name in ("provider", "requested_model", "actual_model")
        ):
            return None
        entry = CatalogVectorEntry(
            fingerprint,
            _vectors(value["vectors"], count=count, dimensions=value["dimensions"]),
            value["provider"],
            value["requested_model"],
            value["actual_model"],
            value["dimensions"],
            float(value["created_at"]),
        )
        if entry.provider_name.casefold() != key[2] or entry.requested_model.casefold() != key[3]:
            return None
        return entry if entry_is_fresh(entry) else None
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        # The disposable cache never becomes a staffing availability gate.
        return None


def _write(directory: Path, key: CatalogCacheKey, value: dict) -> None:
    ensure_private_directory(directory)
    path = _slot(directory, key)
    if os.path.lexists(path) and not _trusted_file(path):
        raise ValueError("unsafe catalog cache target")
    payload = json.dumps(value, allow_nan=False, separators=(",", ":"))
    if len(payload.encode()) > MAX_CATALOG_CACHE_BYTES:
        raise ValueError("catalog cache size limit")
    validate_private_directory(directory)
    atomic_write_text(path, payload)
    restrict_private_file(path)


def save_catalog_vectors(
    directory: Path | None, key: CatalogCacheKey, entry: CatalogVectorEntry
) -> None:
    if directory is None:
        return
    try:
        count = len(entry.document_vectors)
        if count * entry.dimensions > MAX_CATALOG_VECTOR_VALUES:
            return
        values = array("d", (value for row in entry.document_vectors for value in row))
        if values.itemsize != 8:
            return
        if sys.byteorder != "little":
            values.byteswap()
        _write(
            directory,
            key,
            {
                "version": 1,
                "key": list(key),
                "fingerprint": entry.catalog_fingerprint,
                "provider": entry.provider_name,
                "requested_model": entry.requested_model,
                "actual_model": entry.actual_model,
                "dimensions": entry.dimensions,
                "created_at": entry.created_at,
                "vectors": base64.b64encode(values.tobytes()).decode("ascii"),
            },
        )
    except (OSError, ValueError, TypeError, OverflowError):
        return


def invalidate_catalog_vectors(directory: Path | None, key: CatalogCacheKey) -> None:
    if directory is None:
        return
    try:
        _read(directory, key)
        # A tombstone avoids unlinking arbitrary files. A concurrent rebuild
        # may be lost, but the consequence is only another cold call.
        _write(directory, key, {})
    except (OSError, ValueError, TypeError):
        return
