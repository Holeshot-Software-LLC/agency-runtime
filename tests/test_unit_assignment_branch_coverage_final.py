"""Exact residual branch coverage for unit-assignment candidate bookkeeping."""

from __future__ import annotations

from typing import Any

from agency_runtime.core import unit_assignment


def test_assignment_catalog_skips_empty_and_duplicate_normalized_slugs() -> None:
    catalog = [
        {"slug": "", "name": "empty"},
        {"slug": "Reviewer", "name": "first"},
        {"agent_slug": "reviewer", "name": "duplicate"},
    ]

    catalog_list, catalog_by_slug = unit_assignment._assignment_catalog(catalog)

    assert catalog_list == catalog
    assert catalog_by_slug == {"reviewer": catalog[1]}


def test_assignment_candidate_does_not_duplicate_a_matched_work_unit() -> None:
    candidates: dict[str, dict[str, Any]] = {}
    catalog = {"reviewer": {"slug": "reviewer", "name": "Reviewer"}}

    unit_assignment._add_assignment_candidate(
        candidates,
        catalog,
        "reviewer",
        "unit-1234567890",
        primary=True,
    )
    unit_assignment._add_assignment_candidate(
        candidates,
        catalog,
        "reviewer",
        "unit-1234567890",
        primary=False,
    )

    assert candidates["reviewer"]["matched_work_unit_ids"] == ["unit-1234567890"]
    assert candidates["reviewer"]["primary_work_unit_ids"] == ["unit-1234567890"]
