"""Credential-free identities for durable roster sources."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit

__all__ = [
    "MAX_DURABLE_SOURCE_BYTES",
    "MAX_DURABLE_SOURCE_COUNT",
    "MAX_SOURCE_DISPLAY_NAME_BYTES",
    "LegacySourceRedaction",
    "SourceIdentityError",
    "canonical_source_display_name",
    "canonical_source_identity",
    "is_legacy_source_redaction_identity",
    "legacy_source_name_redaction",
    "legacy_source_redaction",
]

MAX_DURABLE_SOURCE_BYTES = 16 * 1024
MAX_DURABLE_SOURCE_COUNT = 256
MAX_SOURCE_DISPLAY_NAME_BYTES = 1024
_NETWORK_SCHEMES = frozenset({"http", "https"})
_URL_SCHEMES = frozenset({"file", *_NETWORK_SCHEMES})
_REDACTED_IDENTITY_RE = re.compile(r"redacted://legacy-source/[a-f0-9]{64}(?:-[1-9][0-9]*)?\Z")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


class SourceIdentityError(ValueError):
    """A source cannot be represented as a safe durable identity."""


@dataclass(frozen=True, slots=True)
class LegacySourceRedaction:
    """Nonsecret replacement evidence for one unsafe legacy source row."""

    identity: str
    reason: str
    purge_references: bool


def _bounded_source(value: object) -> str:
    if not isinstance(value, str):
        raise SourceIdentityError("source URL must be text")
    if not value:
        raise SourceIdentityError("source URL may not be empty")
    if not value.strip():
        raise SourceIdentityError("source URL may not be blank")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise SourceIdentityError("source URL is not valid UTF-8 text") from None
    if len(encoded) > MAX_DURABLE_SOURCE_BYTES:
        raise SourceIdentityError(f"source URL exceeds {MAX_DURABLE_SOURCE_BYTES} UTF-8 bytes")
    if _contains_durable_control(value):
        raise SourceIdentityError("source URL may not contain control characters")
    return value


def _contains_durable_control(value: str) -> bool:
    return any(
        ord(character) <= 0x1F
        or 0x7F <= ord(character) <= 0x9F
        or unicodedata.category(character) == "Cf"
        for character in value
    )


def _split_source(value: str) -> SplitResult:
    try:
        return urlsplit(value)
    except ValueError:
        raise SourceIdentityError("source URL is malformed") from None


def _is_url(parsed: SplitResult) -> bool:
    return bool(parsed.netloc or parsed.scheme.casefold() in _URL_SCHEMES)


def _canonical_authority(parsed: SplitResult) -> str:
    hostname = parsed.hostname
    if not hostname:
        raise SourceIdentityError("source URL must include a hostname")
    try:
        port = parsed.port
    except ValueError:
        raise SourceIdentityError("source URL has an invalid port") from None
    host = hostname.casefold()
    if ":" in host:
        host = f"[{host}]"
    return f"{host}:{port}" if port is not None else host


def canonical_source_identity(value: object) -> str:
    """Validate and canonicalize a source that is safe to persist and display.

    Durable sources are intentionally unauthenticated. Query strings,
    fragments, and URL userinfo are rejected rather than silently changing the
    future fetch target.
    """

    source = _bounded_source(value)
    if source.startswith(("\\\\", "//")):
        raise SourceIdentityError("remote filesystem roster paths are not supported")
    parsed = _split_source(source)
    scheme = parsed.scheme.casefold()
    if scheme and scheme not in _URL_SCHEMES and not _WINDOWS_DRIVE_RE.match(source):
        raise SourceIdentityError("source URL uses an unsupported scheme")
    if parsed.query:
        raise SourceIdentityError("source URL may not contain a query")
    if parsed.fragment:
        raise SourceIdentityError("source URL may not contain a fragment")
    if not _is_url(parsed):
        return source
    if parsed.username is not None or parsed.password is not None:
        raise SourceIdentityError("source URL may not contain credentials")

    if scheme in _NETWORK_SCHEMES:
        if any(character.isspace() for character in source) or "\\" in source:
            raise SourceIdentityError("source URL may not contain whitespace or a backslash")
        try:
            source.encode("ascii")
        except UnicodeEncodeError:
            raise SourceIdentityError(
                "source URL must percent-encode non-ASCII characters"
            ) from None
        authority = _canonical_authority(parsed)
        return urlunsplit((scheme, authority, parsed.path, "", ""))

    if parsed.netloc and parsed.netloc.casefold() != "localhost":
        raise SourceIdentityError("remote file URL authorities are not supported")
    authority = "localhost" if parsed.netloc else ""
    return urlunsplit((scheme, authority, parsed.path, "", ""))


def canonical_source_display_name(
    value: object,
    *,
    source_identity: str,
    source_input: object,
) -> str:
    """Return a bounded label that cannot reintroduce URL credentials.

    Ordinary human labels are preserved. URL-shaped labels receive the same
    credential and scheme validation as durable source identities.
    """

    if value in (None, "") or value == source_input:
        return source_identity
    if not isinstance(value, str):
        raise SourceIdentityError("source name must be text")
    if not value.strip():
        raise SourceIdentityError("source name may not be blank")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise SourceIdentityError("source name is not valid UTF-8 text") from None
    if len(encoded) > MAX_SOURCE_DISPLAY_NAME_BYTES:
        raise SourceIdentityError(
            f"source name exceeds {MAX_SOURCE_DISPLAY_NAME_BYTES} UTF-8 bytes"
        )
    if _contains_durable_control(value):
        raise SourceIdentityError("source name may not contain control characters")
    parsed = _split_source(value)
    if parsed.netloc or parsed.scheme.casefold() in _URL_SCHEMES or "://" in value:
        return canonical_source_identity(value)
    return value


def is_legacy_source_redaction_identity(value: object) -> bool:
    """Return whether a value is one exact opaque v30 migration marker."""

    return isinstance(value, str) and _REDACTED_IDENTITY_RE.fullmatch(value) is not None


def legacy_source_redaction(
    value: object,
    *,
    source_id: object,
) -> LegacySourceRedaction | None:
    """Return an opaque replacement when a legacy URL may contain credentials."""

    storage_is_text = isinstance(value, str)
    undecodable_bytes = False
    if storage_is_text:
        source = value
    elif isinstance(value, bytes):
        try:
            source = value.decode("utf-8")
        except UnicodeDecodeError:
            source = ""
            undecodable_bytes = True
    else:
        source = str(value or "")
    if is_legacy_source_redaction_identity(value):
        return None
    unsafe_control = _contains_durable_control(source)
    try:
        parsed = urlsplit(source)
    except ValueError:
        parsed = None
    malformed_url = parsed is None and "://" in source
    sensitive_components = bool(
        undecodable_bytes
        or unsafe_control
        or (
            parsed is not None
            and (
                parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
            )
        )
    )
    if storage_is_text:
        try:
            canonical_source_identity(source)
        except SourceIdentityError:
            pass
        else:
            return None

    if undecodable_bytes:
        reason = "unreadable_source_bytes"
        purge_references = True
    elif unsafe_control:
        reason = "unsafe_source_controls"
        purge_references = True
    elif malformed_url:
        reason = "malformed_url"
        purge_references = True
    elif sensitive_components:
        reason = "credentials_or_opaque_components"
        purge_references = True
    elif not storage_is_text:
        reason = "invalid_source_storage_type"
        purge_references = False
    else:
        reason = "unsupported_or_noncanonical_source"
        purge_references = False
    digest = hashlib.sha256(str(source_id or "").encode("utf-8")).hexdigest()
    return LegacySourceRedaction(
        identity=f"redacted://legacy-source/{digest}",
        reason=reason,
        purge_references=purge_references,
    )


def legacy_source_name_redaction(
    value: object,
    *,
    source_id: object,
) -> LegacySourceRedaction | None:
    """Classify an unsafe legacy source label without treating prose as a URL."""

    if not isinstance(value, str):
        return legacy_source_redaction(value, source_id=f"{source_id}:name")
    name = value
    if is_legacy_source_redaction_identity(name):
        return None
    if _contains_durable_control(name):
        digest = hashlib.sha256(f"{source_id}:name".encode()).hexdigest()
        return LegacySourceRedaction(
            identity=f"redacted://legacy-source/{digest}",
            reason="unsafe_source_name",
            purge_references=True,
        )
    try:
        canonical_source_display_name(
            name,
            source_identity="legacy-source",
            source_input=None,
        )
    except SourceIdentityError:
        redaction = legacy_source_redaction(name, source_id=f"{source_id}:name")
        if redaction is None:  # pragma: no cover - guarded redaction marker contract
            raise RuntimeError("legacy source-name classification was inconsistent") from None
        return redaction
    return None
