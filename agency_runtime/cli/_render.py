"""Plain-text card-style output helpers for the Agency Runtime CLI.

The first slice is intentionally a thin wrapper around tab-separated text so
that the cross-cutting CLI presentation richness work (sub-issue 10 in
AR-236) can pick a presentation library without rewriting every existing
command. Color, live-watch, and `rich` integration are deferred.

Cards are grouped by status, separated by horizontal rules, and laid out so a
human reader can scan them top-to-bottom. A single card carries a title line,
one tab-aligned field block, and an optional evidence block whose labels
mirror the dashboard's `HIRING_EVIDENCE_DOCUMENTS` ordering.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

DEFAULT_CARD_WIDTH = 72
DEFAULT_DIVIDER = "─" * DEFAULT_CARD_WIDTH

HIRING_EVIDENCE_LABELS: tuple[tuple[str, str], ...] = (
    ("gap_evidence", "Gap evidence"),
    ("duplicate_evidence", "Duplicate analysis"),
    ("contract_evidence", "Contract evidence"),
    ("critic_evidence", "Independent critic"),
    ("model_evidence", "Model receipts"),
)


def _isatty() -> bool:
    import sys

    stream = sys.stdout
    return bool(getattr(stream, "isatty", lambda: False)())


def use_card_default(args: Any) -> bool:
    """Return the resolved default for ``--card`` when the flag is absent.

    Card mode is on-by-default when stdout is a TTY and the caller has not
    already asked for ``--json``. The flag itself always wins.
    """

    if getattr(args, "json", False):
        return False
    if getattr(args, "card", None) is True:
        return True
    if getattr(args, "card", None) is False:
        return False
    return _isatty()


def divider(char: str = "─", width: int = DEFAULT_CARD_WIDTH) -> str:
    """Return a horizontal rule with the given character and width."""

    if width <= 0:
        return ""
    return char * width


def _truncate(text: str, *, maximum: int) -> str:
    if maximum <= 1:
        return text[:maximum]
    if len(text) <= maximum:
        return text
    return text[: maximum - 1] + "…"


def _format_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (str, int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


@dataclass(frozen=True, slots=True)
class CardField:
    """One tab-aligned row inside a card field block."""

    label: str
    value: Any
    placeholder: str = "—"


@dataclass(frozen=True, slots=True)
class CardSection:
    """A titled evidence or detail block under a card's primary field block."""

    title: str
    body: str
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class Card:
    """A single bounded card layout ready to be printed.

    ``title`` is the headline (the proposed slug, a worker name, etc.).
    ``subtitle`` is the right-aligned secondary headline (e.g. ``hire ·
    proposed``). Both are truncated together so the rendered line never
    exceeds the configured card width.
    """

    title: str
    subtitle: str = ""
    fields: tuple[CardField, ...] = ()
    sections: tuple[CardSection, ...] = ()
    width: int = DEFAULT_CARD_WIDTH
    notes: tuple[str, ...] = field(default_factory=tuple)

    def render(self) -> str:
        lines: list[str] = []
        lines.append(divider(width=self.width))
        head = self._head_line()
        if head:
            lines.append(head)
        if self.fields:
            lines.append(divider(width=self.width))
            lines.extend(self._render_fields())
        for section in self.sections:
            lines.append(divider(width=self.width))
            lines.append(self._section_title(section.title))
            lines.append(divider(width=self.width))
            lines.append(section.body)
        if self.notes:
            lines.append(divider(width=self.width))
            lines.extend(self.notes)
        lines.append(divider(width=self.width))
        return "\n".join(lines)

    def _head_line(self) -> str:
        title = _truncate(self.title or "", maximum=max(1, self.width // 2))
        if not self.subtitle:
            return title
        subtitle = _truncate(self.subtitle, maximum=max(1, self.width // 2))
        padding = max(1, self.width - len(title) - len(subtitle))
        return f"{title}{' ' * padding}{subtitle}"

    def _render_fields(self) -> list[str]:
        label_width = max(len(field.label) for field in self.fields)
        rows: list[str] = []
        for field_ in self.fields:
            label = field_.label.ljust(label_width)
            value = _format_value(field_.value)
            if value == "—":
                value = field_.placeholder
            value = _truncate(value, maximum=max(1, self.width - label_width - 2))
            rows.append(f"{label}\t{value}")
        return rows

    @staticmethod
    def _section_title(title: str) -> str:
        return title.strip()


def render_cards(cards: Sequence[Card]) -> str:
    """Render zero or more cards, separated by a blank line."""

    if not cards:
        return ""
    return "\n\n".join(card.render() for card in cards)


def field(label: str, value: Any, *, placeholder: str = "—") -> CardField:
    return CardField(label=label, value=value, placeholder=placeholder)


def section(
    title: str,
    body: Mapping[str, Any] | str,
    *,
    maximum_bytes: int = 4096,
) -> CardSection:
    """Build one bounded evidence section from a JSON-shaped mapping or string."""

    if isinstance(body, str):
        encoded = body
    else:
        encoded = json.dumps(dict(body), ensure_ascii=False, indent=2, sort_keys=True)
    truncated = False
    if len(encoded.encode("utf-8")) > maximum_bytes:
        encoded = encoded.encode("utf-8")[: max(0, maximum_bytes - 1)].decode(
            "utf-8", errors="backslashreplace"
        )
        truncated = True
    return CardSection(title=title, body=encoded, truncated=truncated)


def from_mapping(
    *,
    title: str,
    subtitle: str = "",
    fields: Iterable[tuple[str, Any]] = (),
    sections: Iterable[tuple[str, Mapping[str, Any] | str]] = (),
    notes: Iterable[str] = (),
    width: int = DEFAULT_CARD_WIDTH,
) -> Card:
    """Build a card from raw tuples (used by call sites that already have dicts)."""

    return Card(
        title=title,
        subtitle=subtitle,
        fields=tuple(field(label, value) for label, value in fields),
        sections=tuple(section(title_label, body) for title_label, body in sections),
        notes=tuple(notes),
        width=width,
    )
