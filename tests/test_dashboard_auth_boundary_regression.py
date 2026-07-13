"""Regression tests for fail-closed dashboard authentication boundaries."""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace

import pytest

from agency_runtime.server.dashboard import DashboardHTTPHandler


@pytest.mark.parametrize(
    "authorization",
    [
        "Bearer caf\N{LATIN SMALL LETTER E WITH ACUTE}",
        "Bearer " + ("x" * 8193),
    ],
    ids=["non-ascii", "oversized"],
)
def test_dashboard_rejects_unsafe_authorization_without_compare_error(
    authorization: str,
) -> None:
    errors: list[tuple[int, str]] = []
    handler = SimpleNamespace(
        headers={"Authorization": authorization},
        auth_token="expected-token",
        _valid_host_header=lambda: True,
        _json_error=lambda status, message: errors.append((status, message)),
    )

    accepted = DashboardHTTPHandler._authorise_api_request(handler)  # type: ignore[arg-type]

    assert accepted is False
    assert errors == [(HTTPStatus.UNAUTHORIZED, "authentication required")]


def test_dashboard_accepts_exact_ascii_bearer_token() -> None:
    errors: list[tuple[int, str]] = []
    handler = SimpleNamespace(
        headers={"Authorization": "Bearer expected-token"},
        auth_token="expected-token",
        _valid_host_header=lambda: True,
        _json_error=lambda status, message: errors.append((status, message)),
    )

    accepted = DashboardHTTPHandler._authorise_api_request(handler)  # type: ignore[arg-type]

    assert accepted is True
    assert errors == []


@pytest.mark.parametrize(
    "auth_token",
    [
        "caf\N{LATIN SMALL LETTER E WITH ACUTE}",
        "x" * 8193,
    ],
    ids=["non-ascii", "oversized"],
)
def test_dashboard_rejects_unsafe_configured_token_without_compare_error(
    auth_token: str,
) -> None:
    errors: list[tuple[int, str]] = []
    handler = SimpleNamespace(
        headers={"Authorization": "Bearer wrong-ascii-token"},
        auth_token=auth_token,
        _valid_host_header=lambda: True,
        _json_error=lambda status, message: errors.append((status, message)),
    )

    accepted = DashboardHTTPHandler._authorise_api_request(handler)  # type: ignore[arg-type]

    assert accepted is False
    assert errors == [(HTTPStatus.UNAUTHORIZED, "authentication required")]
