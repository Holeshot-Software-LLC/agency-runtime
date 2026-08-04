"""Coverage for the CLI card render helpers in ``agency_runtime.cli._render``."""

from __future__ import annotations

import argparse
import json

import pytest

from agency_runtime.cli import _render


def _args(card=None, json=False):
    return argparse.Namespace(card=card, json=json)


def test_use_card_default_resolves_to_false_when_json_is_set() -> None:
    args = _args(card=None, json=True)
    assert _render.use_card_default(args) is False


def test_use_card_default_resolves_to_true_when_card_flag_set(monkeypatch) -> None:
    monkeypatch.setattr(_render, "_isatty", lambda: False)
    args = _args(card=True, json=False)
    assert _render.use_card_default(args) is True


def test_use_card_default_resolves_to_true_when_stdout_is_a_tty(monkeypatch) -> None:
    monkeypatch.setattr(_render, "_isatty", lambda: True)
    args = _args(card=None, json=False)
    assert _render.use_card_default(args) is True


def test_use_card_default_resolves_to_false_when_stdout_is_not_a_tty(monkeypatch) -> None:
    monkeypatch.setattr(_render, "_isatty", lambda: False)
    args = _args(card=None, json=False)
    assert _render.use_card_default(args) is False


def test_divider_uses_default_width() -> None:
    assert len(_render.divider()) == _render.DEFAULT_CARD_WIDTH
    assert _render.divider("=") == "=" * _render.DEFAULT_CARD_WIDTH


def test_field_renders_truthy_value_as_text() -> None:
    rendered = _render.from_mapping(
        title="title",
        fields=(("Slug", "ops-reviewer"), ("Risk", "high")),
    ).render()
    assert "Slug" in rendered
    assert "ops-reviewer" in rendered
    assert "Risk" in rendered
    assert "high" in rendered


def test_field_uses_placeholder_when_value_is_none() -> None:
    rendered = _render.from_mapping(
        title="title",
        fields=(("Approved by", None),),
    ).render()
    assert "Approved by" in rendered
    assert "—" in rendered


def test_section_serializes_mapping_to_indented_json() -> None:
    rendered = _render.from_mapping(
        title="title",
        sections=(("Evidence", {"answer": 42, "ok": True}),),
    ).render()
    assert "Evidence" in rendered
    lines = rendered.splitlines()
    divider = _render.divider()
    title_index = lines.index("Evidence")
    body_lines: list[str] = []
    for line in lines[title_index + 2 :]:
        if line == divider:
            break
        body_lines.append(line)
    body = json.loads("\n".join(body_lines))
    assert body == {"answer": 42, "ok": True}


def test_section_truncates_oversize_body() -> None:
    big_body = {"blob": "x" * 10_000}
    rendered = _render.from_mapping(
        title="title",
        sections=(("Big", big_body),),
    ).render()
    truncated_section = next(
        section for section in rendered.split(_render.divider()) if "Big" in section
    )
    assert "…" not in truncated_section or "truncated" in rendered.lower()


def test_render_cards_separates_cards_with_blank_line() -> None:
    cards = [
        _render.from_mapping(title="A", fields=(("k", "v1"),)),
        _render.from_mapping(title="B", fields=(("k", "v2"),)),
    ]
    output = _render.render_cards(cards)
    assert output.count(_render.divider()) >= 4
    assert "\n\n" in output


def test_hiring_evidence_labels_match_dashboard_ordering() -> None:
    assert _render.HIRING_EVIDENCE_LABELS[0][0] == "gap_evidence"
    assert _render.HIRING_EVIDENCE_LABELS[-1][0] == "model_evidence"
    assert "contract_evidence" in {name for name, _label in _render.HIRING_EVIDENCE_LABELS}


@pytest.mark.parametrize("value", [True, False])
def test_field_renders_boolean_as_yes_or_no(value: bool) -> None:
    rendered = _render.from_mapping(
        title="title",
        fields=(("Approved", value),),
    ).render()
    expected = "yes" if value else "no"
    assert expected in rendered
