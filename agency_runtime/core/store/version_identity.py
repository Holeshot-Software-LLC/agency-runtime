"""Bounded opaque identities for immutable specialist prompt versions."""

from __future__ import annotations

from hashlib import sha256

MAX_VERSION_IDENTITY_BYTES = 256


def normalize_version_identity(
    value: object,
    *,
    fallback_content: str | None = None,
) -> str:
    """Return one safe upstream identity, deriving a digest when absent.

    Roster sources historically use both SHA-256 digests and bounded opaque
    version hashes. Replay needs an exact immutable identifier, not a claim
    that every upstream source uses one digest algorithm.
    """

    normalized = str(value or "").strip()
    if not normalized and fallback_content is not None:
        normalized = sha256(fallback_content.encode("utf-8")).hexdigest()
    if (
        not normalized
        or len(normalized.encode("utf-8", errors="surrogatepass")) > MAX_VERSION_IDENTITY_BYTES
        or any(ord(character) < 32 or ord(character) == 127 for character in normalized)
    ):
        raise ValueError("specialist version hash must be a bounded opaque identifier")
    return normalized


def is_valid_version_identity(value: object) -> bool:
    try:
        normalize_version_identity(value)
    except ValueError:
        return False
    return True


__all__ = [
    "MAX_VERSION_IDENTITY_BYTES",
    "is_valid_version_identity",
    "normalize_version_identity",
]
