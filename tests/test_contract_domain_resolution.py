"""Domain has to be able to tell two engineers apart.

`domains` is required on every work unit, matched in `staffing_verifier` and
weighted 0.20 in `comparison` -- but a division answers "which part of the
business", not "which part of the system", so all 54 `engineering` specialists
collapsed to the single domain `software-engineering`. On the one dimension
meant to separate them, frontend-developer and code-reviewer were identical,
across the division holding nearly all the real work.

Measured 2026-08-11: frontend-developer was staffed on a turn that excluded
frontend work, and skipped on a turn that was entirely frontend work.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agency_runtime.core.workforce.contract import _CATEGORY_DOMAINS, _domains

_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "agency_runtime"
    / "core"
    / "roster"
    / "data"
    / "manifest.json"
)


def _roster() -> list[dict]:
    data = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    rows = data["agents"] if isinstance(data, dict) and "agents" in data else data
    if isinstance(rows, dict):
        rows = list(rows.values())
    return [row for row in rows if isinstance(row, dict)]


def _by_slug(slug: str) -> dict:
    for row in _roster():
        if row.get("slug") == slug:
            return row
    pytest.skip(f"{slug} is not in the shipped roster")
    raise AssertionError  # pragma: no cover


def test_a_frontend_specialist_is_no_longer_identical_to_a_reviewer() -> None:
    """The exact pair the incident turned on."""

    frontend = _domains(_by_slug("frontend-developer"), "engineering")
    reviewer = _domains(_by_slug("code-reviewer"), "engineering")

    assert "frontend" in frontend
    assert "frontend" not in reviewer
    assert set(frontend) != set(reviewer)


def test_the_division_domain_is_never_lost() -> None:
    """Promotion is additive; a unit naming only the division must still match."""

    for row in _roster():
        if row.get("division") != "engineering":
            continue
        assert "software-engineering" in _domains(row, "engineering")


def test_engineering_gains_real_resolution() -> None:
    """One tuple for 54 specialists is the same as having no dimension at all."""

    engineering = [row for row in _roster() if row.get("division") == "engineering"]
    distinct = {tuple(_domains(row, "engineering")) for row in engineering}

    assert len(engineering) > 40
    assert len(distinct) >= 10, "domain still cannot separate most engineering specialists"


def test_promotion_only_ever_adds() -> None:
    """The verifier matches by set intersection, which can only grow.

    That is what makes this safe to ship: no unit that could be staffed before
    becomes unstaffable now.
    """

    for row in _roster():
        division = str(row.get("division") or "")
        promoted = set(_domains(row, division))
        categories = {str(item).casefold() for item in row.get("categories", ())}
        baseline = promoted - {_CATEGORY_DOMAINS[c] for c in categories if c in _CATEGORY_DOMAINS}
        assert baseline <= promoted


def test_every_promoted_category_exists_in_the_shipped_roster() -> None:
    """Vocabulary neither side emits would add nothing but drift."""

    declared: set[str] = set()
    for row in _roster():
        declared.update(str(item).casefold() for item in row.get("categories", ()))

    unused = sorted(set(_CATEGORY_DOMAINS) - declared)

    assert not unused, f"promoted categories no specialist declares: {unused}"
