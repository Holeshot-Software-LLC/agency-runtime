"""Resolve a request whose subject is a bare reference (AR-370 / ADR-0211).

"install this: <url>" and "fix that" name no subject retrieval can act on. The
runtime used to hand the raw words to retrieval anyway, get nothing back, and
report the empty result as though the roster had been searched.

What is resolved here is deliberately narrow and deterministic: identifiers the
turn already contains -- the distinctive labels of a URL, or the typed subject
hints the previous turn derived. Nothing is invented, and nothing is inferred;
naming the work is the planner's job, and this only supplies a subject for it
and for retrieval to act on. The resolution is recorded on the routing receipt
so a wrong one is visible rather than silent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final
from urllib.parse import urlsplit

#: A message whose subject is one of these and nothing else names nothing.
_DEICTICS: Final[frozenset[str]] = frozenset(
    {"this", "that", "it", "these", "those", "them", "here", "there"}
)
#: URL parts that identify no subject: they appear on every host or path.
_GENERIC_URL_PARTS: Final[frozenset[str]] = frozenset(
    {
        "www",
        "com",
        "org",
        "net",
        "io",
        "ai",
        "dev",
        "app",
        "co",
        "uk",
        "en",
        "us",
        "http",
        "https",
        "index",
        "html",
        "htm",
        "php",
        "latest",
        "main",
        "master",
        "docs",
        "doc",
        "download",
        "downloads",
        "dist",
        "release",
        "releases",
        "v1",
        "v2",
        "api",
        "static",
        "assets",
        "page",
        "home",
    }
)
_TOKENS: Final[re.Pattern[str]] = re.compile(r"[a-z0-9]+")
_URL: Final[re.Pattern[str]] = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)
#: Bound on what is appended to a query: this supplies a subject, not prose.
MAX_RESOLVED_SUBJECT_CHARS: Final[int] = 120
MAX_RESOLVED_TOKENS: Final[int] = 8

_SUBJECT_HINT_FIELDS: Final[tuple[str, ...]] = (
    "domains",
    "languages",
    "frameworks",
    "capability_ids",
    "platforms",
)


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    """What the turn's bare reference was resolved to, and from where."""

    #: Whether the request's subject was a bare reference at all.
    detected: bool = False
    #: ``url``, ``deictic``, or empty when nothing was detected.
    kind: str = ""
    #: ``url``, ``turn_context``, or empty when nothing could resolve it.
    resolved_from: str = ""
    #: Bounded identifiers, never prose and never model text.
    subject: str = ""

    @property
    def resolved(self) -> bool:
        return bool(self.subject)

    def receipt(self) -> dict[str, Any]:
        """The bounded, content-free view the routing receipt carries."""

        return {
            "detected": self.detected,
            "kind": self.kind,
            "resolved_from": self.resolved_from,
            "resolved_subject": self.subject,
        }


def _bounded(tokens: list[str]) -> str:
    unique = list(dict.fromkeys(tokens))[:MAX_RESOLVED_TOKENS]
    return " ".join(unique)[:MAX_RESOLVED_SUBJECT_CHARS].strip()


def _url_subject(url: str) -> str:
    """Return the distinctive labels of a URL, dropping the parts every URL has."""

    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    labels = [*parts.hostname.split(".")] if parts.hostname else []
    labels.extend(segment for segment in parts.path.split("/") if segment)
    tokens = [
        token
        for label in labels
        for token in _TOKENS.findall(label.casefold())
        if token not in _GENERIC_URL_PARTS and len(token) > 1 and not token.isdigit()
    ]
    return _bounded(tokens)


def _context_subject(turn_context: Any) -> str:
    """Return the typed identifiers the previous turn already derived."""

    if not isinstance(turn_context, dict):
        return ""
    hints = turn_context.get("workforce_subject_hints")
    if not isinstance(hints, dict):
        return ""
    tokens: list[str] = []
    for field in _SUBJECT_HINT_FIELDS:
        values = hints.get(field)
        if isinstance(values, (list, tuple)):
            tokens.extend(
                token for value in values for token in _TOKENS.findall(str(value).casefold())
            )
    return _bounded(tokens)


def mentions_bare_reference(message: str) -> bool:
    """Whether the message contains a URL or a deictic at all.

    A cheap precheck so the caller's retrieval predicate -- a full narrowing
    pass over the eligible catalog -- is only spent on the turns where a
    resolution could possibly apply.
    """

    if not isinstance(message, str) or not message.strip():
        return False
    if _URL.search(message) is not None:
        return True
    return any(token in _DEICTICS for token in _TOKENS.findall(message.casefold()))


def strip_bare_reference(message: str) -> str:
    """Return the message with its URLs and deictics removed.

    The caller asks its own retrieval predicate whether what is left still
    names a subject, which is what decides whether anything needs resolving.
    """

    without_urls = _URL.sub(" ", message if isinstance(message, str) else "")
    return " ".join(
        word
        for word in without_urls.split()
        if "".join(_TOKENS.findall(word.casefold())) not in _DEICTICS
    )


def resolve_bare_reference(
    message: str,
    *,
    subject_is_retrievable: bool,
    turn_context: Any = None,
) -> ResolvedReference:
    """Resolve a request whose subject is a bare deictic or a bare URL.

    ``subject_is_retrievable`` is the caller's own retrieval predicate applied
    to ``strip_bare_reference(message)``: whether the request still names
    something once its bare reference is taken away. Deciding it here would
    mean shipping a list of words that do not count as a subject, which is the
    hand-curated vocabulary this issue exists to remove.

    A request that names its own subject is returned untouched: this supplies a
    subject only where the turn has none.
    """

    if not isinstance(message, str) or not message.strip():
        return ResolvedReference()
    if subject_is_retrievable:
        return ResolvedReference()

    urls = _URL.findall(message)
    has_deictic = any(
        token in _DEICTICS for token in _TOKENS.findall(_URL.sub(" ", message).casefold())
    )
    if urls:
        subject = _url_subject(urls[0])
        return ResolvedReference(
            detected=True,
            kind="url",
            resolved_from="url" if subject else "",
            subject=subject,
        )
    if has_deictic:
        subject = _context_subject(turn_context)
        return ResolvedReference(
            detected=True,
            kind="deictic",
            resolved_from="turn_context" if subject else "",
            subject=subject,
        )
    return ResolvedReference()


__all__ = [
    "MAX_RESOLVED_SUBJECT_CHARS",
    "MAX_RESOLVED_TOKENS",
    "ResolvedReference",
    "mentions_bare_reference",
    "resolve_bare_reference",
    "strip_bare_reference",
]
