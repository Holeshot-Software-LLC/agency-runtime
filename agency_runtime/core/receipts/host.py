"""Generic host model telemetry normalization."""

from __future__ import annotations

from typing import Any, Mapping

from .normalize import normalize_host_receipt


def extract_host_receipt(host_metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a canonical receipt from host-exposed telemetry."""
    return normalize_host_receipt(host_metadata)


__all__ = ["extract_host_receipt", "normalize_host_receipt"]
