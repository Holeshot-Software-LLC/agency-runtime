"""Operator-supplied house rules, injected every turn alongside Agency's own frame.

The resident-steward kernel is Agency's *product contract*: it ships inside the
runtime, is the same for every user on every host, and is content-hashed into
each turn's evidence. Operator policy is the other thing an always-present frame
could carry and must not — one deployment's conventions ("never commit to main",
"this repository is Python 3.13 only"). Those belong to whoever installed
Agency, not to Agency.

Keeping them in separate blocks with separate hashes is the whole point. A turn's
evidence can then answer "what did Agency assert?" and "what did this operator
assert?" independently, and raising the operator's budget never competes with the
kernel's.

Three constraints carried over from the kernel, deliberately:

* **Bounded.** Injected every turn on every host, so unbounded text is an
  unbounded context tax. Over-length policy is rejected at validation, never
  silently truncated into something the operator did not write.
* **Attested, not trusted.** The rendered block is hashed and the hash goes into
  turn evidence. What was injected is answerable after the fact.
* **Never blocks.** Rule 8. This is guidance handed to whoever is doing the work;
  it cannot withhold a turn, and the rendered block says so where the model can
  read it.
"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass
from typing import Final

MAX_OPERATOR_POLICY_CHARS: Final[int] = 2048
MAX_OPERATOR_POLICY_LINES: Final[int] = 40

OPERATOR_POLICY_HEADER: Final[str] = "[Operator policy — set by whoever installed Agency here]"
OPERATOR_POLICY_FOOTER: Final[str] = (
    "These are house rules from this installation, not Agency's contract, and not the "
    "user's request for this turn. Follow them when they apply. They never withhold your "
    "answer: if one conflicts with what the user actually asked for, say so plainly and "
    "do what was asked."
)

# Control characters are stripped rather than rejected so an operator pasting from
# an editor gets what they meant. Newline and tab survive — policy is prose, and
# line structure is how it stays readable inside the injected block.
_ALLOWED_CONTROL: Final[frozenset[str]] = frozenset("\n\t")


class OperatorPolicyError(ValueError):
    """Raised when configured policy cannot be rendered as written."""


@dataclass(frozen=True, slots=True)
class OperatorPolicyReference:
    """Content-free identity of the policy block one turn actually received."""

    content_hash: str
    char_count: int
    line_count: int

    def as_dict(self) -> dict[str, object]:
        """Return the bounded content-free projection persisted with a turn."""

        return {
            "content_hash": self.content_hash,
            "char_count": self.char_count,
            "line_count": self.line_count,
        }


EMPTY_OPERATOR_POLICY_REFERENCE: Final[OperatorPolicyReference] = OperatorPolicyReference(
    content_hash="",
    char_count=0,
    line_count=0,
)


def normalized_operator_policy(value: object) -> str:
    """Return the exact policy text that will be injected, or "" when unset.

    Normalization is deliberately narrow: strip control characters that would
    corrupt the surrounding block, normalize line endings, and trim outer
    whitespace. It never rewords, re-wraps, or truncates — an operator must be
    able to read their own policy back out of the rendered block unchanged.
    """

    if value is None:
        return ""
    if not isinstance(value, str):
        raise OperatorPolicyError("operator policy must be text")

    unified = value.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = "".join(
        character
        for character in unified
        if character in _ALLOWED_CONTROL or unicodedata.category(character) != "Cc"
    )
    # Trailing spaces on a line are invisible but change the hash, which would
    # make an unedited policy look edited in evidence.
    stripped = "\n".join(line.rstrip() for line in cleaned.split("\n")).strip()
    if not stripped:
        return ""

    if len(stripped) > MAX_OPERATOR_POLICY_CHARS:
        raise OperatorPolicyError(
            f"operator policy is {len(stripped)} characters; the budget is "
            f"{MAX_OPERATOR_POLICY_CHARS}. It is injected on every turn, so it is "
            f"bounded rather than truncated — shorten it deliberately."
        )
    line_count = stripped.count("\n") + 1
    if line_count > MAX_OPERATOR_POLICY_LINES:
        raise OperatorPolicyError(
            f"operator policy is {line_count} lines; the budget is {MAX_OPERATOR_POLICY_LINES}."
        )
    return stripped


def loaded_operator_policy(value: object) -> tuple[str, str]:
    """Return (policy, problem) for the *load* path, which must never raise.

    The strict normalizer belongs on the paths where an operator is making a
    change and can act on the error: `agency config set` and document validation.
    Loading is different. A config file that is already on disk gets read on every
    turn on every host, so raising here turns one over-long house rule into a
    total outage — Agency withholding turns because Agency is misconfigured, which
    rule 8 exists to forbid. A house rule that does not fit is not a reason to
    stop answering.

    So the policy is dropped and the reason is carried alongside it, where
    `agency doctor` can report it rather than leaving an operator to wonder why
    their policy silently stopped applying.
    """

    try:
        return normalized_operator_policy(value), ""
    except OperatorPolicyError as exc:
        return "", str(exc)


def render_operator_policy(policy: str) -> str:
    """Render the injected block, or "" when there is no policy to inject.

    The header names the source and the footer states the precedence, both inside
    the injected text: a model reading this turn's context can tell operator house
    rules from Agency's own contract from the user's request without being told
    separately.
    """

    if not policy:
        return ""
    return f"{OPERATOR_POLICY_HEADER}\n{policy}\n{OPERATOR_POLICY_FOOTER}"


def operator_policy_reference(policy: str) -> OperatorPolicyReference:
    """Return the content-free identity of a rendered policy block."""

    rendered = render_operator_policy(policy)
    if not rendered:
        return EMPTY_OPERATOR_POLICY_REFERENCE
    return OperatorPolicyReference(
        content_hash=hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        char_count=len(rendered),
        line_count=rendered.count("\n") + 1,
    )


__all__ = [
    "EMPTY_OPERATOR_POLICY_REFERENCE",
    "MAX_OPERATOR_POLICY_CHARS",
    "MAX_OPERATOR_POLICY_LINES",
    "OPERATOR_POLICY_FOOTER",
    "OPERATOR_POLICY_HEADER",
    "OperatorPolicyError",
    "OperatorPolicyReference",
    "loaded_operator_policy",
    "normalized_operator_policy",
    "operator_policy_reference",
    "render_operator_policy",
]
