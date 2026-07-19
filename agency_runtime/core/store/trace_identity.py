"""Content-free retired-correlation identity helpers."""

from __future__ import annotations

import hmac
from hashlib import sha256
from typing import Any

_KEY_NAME = "retired-trace-hmac-v1"
_KEY_VERIFIER_NAME = "retired-trace-hmac-v1-verifier"
_KEY_VERIFIER_PAYLOAD = b"agency-runtime:retired-trace-key-verifier:v1"


def _key_verifier(key: bytes) -> bytes:
    return hmac.new(key, _KEY_VERIFIER_PAYLOAD, sha256).digest()


def ensure_correlation_key_integrity(
    conn: Any,
    *,
    allow_initialize: bool,
) -> bytes:
    """Return the store key only when its durable identity is intact.

    A fixed verifier detects deletion, truncation, and accidental valid-length
    replacement of the HMAC key before a retired trace can be resurrected. The
    verifier is initialized only while upgrading a pre-v16 schema; a current
    schema with missing integrity state fails closed.
    """

    rows = {
        str(row["name"]): bytes(row["secret"])
        for row in conn.execute(
            "SELECT name, secret FROM store_secrets WHERE name IN (?, ?)",
            (_KEY_NAME, _KEY_VERIFIER_NAME),
        ).fetchall()
    }
    key = rows.get(_KEY_NAME)
    if key is None:
        raise RuntimeError("retired-trace integrity key is unavailable")
    if len(key) != 32:
        raise RuntimeError("retired-trace integrity key is invalid")
    expected = _key_verifier(key)
    verifier = rows.get(_KEY_VERIFIER_NAME)
    if verifier is None:
        if not allow_initialize:
            raise RuntimeError("retired-trace integrity key verifier is unavailable")
        conn.execute(
            "INSERT INTO store_secrets (name, secret, created_at) "
            "VALUES (?, ?, STRFTIME('%Y-%m-%dT%H:%M:%f000+00:00', 'NOW'))",
            (_KEY_VERIFIER_NAME, expected),
        )
    elif not hmac.compare_digest(verifier, expected):
        raise RuntimeError("retired-trace integrity key verifier does not match")
    return key


def _store_key(conn: Any) -> bytes:
    return ensure_correlation_key_integrity(conn, allow_initialize=False)


def _digest_with_key(key: bytes, value: str, *, domain: str) -> str:
    normalized_value = str(value or "")
    normalized_domain = str(domain or "").strip()
    if normalized_domain not in {"session", "trace"} or (
        normalized_domain == "trace" and not normalized_value
    ):
        raise ValueError("correlation value and supported digest domain are required")
    if normalized_domain == "session" and not normalized_value:
        normalized_value = "<uncorrelated-session>"
    payload = f"agency-runtime:{normalized_domain}:v1\0{normalized_value}".encode(
        "utf-8",
        errors="surrogatepass",
    )
    return hmac.new(key, payload, sha256).hexdigest()


def correlation_digest(conn: Any, value: str, *, domain: str) -> str:
    """Return a domain-separated HMAC without retaining caller identity text."""

    return _digest_with_key(_store_key(conn), value, domain=domain)


def correlation_pair_digests(
    conn: Any,
    *,
    trace_id: str,
    session_id: str,
) -> tuple[str, str]:
    """Digest one trace/session pair with a single verified key read."""

    key = _store_key(conn)
    return (
        _digest_with_key(key, trace_id, domain="trace"),
        _digest_with_key(key, session_id, domain="session"),
    )


__all__ = [
    "correlation_digest",
    "correlation_pair_digests",
    "ensure_correlation_key_integrity",
]
