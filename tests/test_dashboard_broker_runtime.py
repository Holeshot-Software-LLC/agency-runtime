"""Restricted Codex dashboard broker credential tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agency_runtime.core import dashboard_broker_runtime as broker_runtime
from agency_runtime.core import dashboard_runtime


def _prepare_home(tmp_path: Path) -> None:
    (tmp_path / ".codex").mkdir()


def test_broker_descriptor_round_trip_never_serializes_plaintext_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_home(tmp_path)
    monkeypatch.setattr(broker_runtime, "storage_parent_is_trusted", lambda *_a, **_k: True)
    token = "restricted-broker-token-" + ("x" * 40)

    target = broker_runtime.write_codex_dashboard_broker(
        token=token,
        port=7810,
        pid=123,
        started_at="2026-07-22T12:00:00+00:00",
        home_dir=tmp_path,
        is_windows=True,
        protector=lambda _value: "protected-" + ("p" * 48),
    )
    descriptor = broker_runtime.read_codex_dashboard_broker(
        home_dir=tmp_path,
        require_attestation=False,
        is_windows=True,
        unprotector=lambda _value: token,
    )

    assert target is not None
    assert token not in target.read_text(encoding="utf-8")
    assert descriptor == {
        "schema_version": 1,
        "pid": 123,
        "port": 7810,
        "token": token,
        "started_at": "2026-07-22T12:00:00+00:00",
    }


def test_broker_descriptor_requires_an_attested_restricted_codex_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_home(tmp_path)
    monkeypatch.setattr(broker_runtime, "storage_parent_is_trusted", lambda *_a, **_k: True)

    with pytest.raises(ValueError, match="brokerage is unavailable"):
        broker_runtime.read_codex_dashboard_broker(
            home_dir=tmp_path,
            environment={},
            is_windows=True,
            unprotector=lambda value: value,
        )


@pytest.mark.skipif(os.name != "nt", reason="requires Windows DPAPI")
def test_windows_dpapi_round_trip_is_user_bound_and_not_plaintext() -> None:
    token = "dpapi-broker-token-" + ("x" * 40)

    protected = broker_runtime._protect_token(token)

    assert token not in protected
    assert broker_runtime._unprotect_token(protected) == token


def test_dashboard_request_falls_back_to_attested_broker_descriptor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor = {
        "schema_version": 1,
        "pid": 123,
        "port": 7810,
        "token": "fallback-broker-token-" + ("x" * 40),
        "started_at": "2026-07-22T12:00:00+00:00",
    }
    monkeypatch.setattr(
        dashboard_runtime,
        "read_dashboard_runtime",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("private descriptor denied")),
    )
    monkeypatch.setattr(
        broker_runtime,
        "read_codex_dashboard_broker",
        lambda **_kwargs: descriptor,
    )

    assert (
        dashboard_runtime._dashboard_request_descriptor(
            descriptor=None,
            home_dir=None,
        )
        == descriptor
    )


def test_broker_descriptor_schema_rejects_plaintext_and_extra_fields() -> None:
    with pytest.raises(ValueError, match="invalid"):
        broker_runtime._validate_public_descriptor(
            {
                "schema_version": 1,
                "audience": "codex-restricted-windows",
                "pid": 123,
                "port": 7810,
                "token": "plaintext",
                "protected_token": "p" * 64,
                "started_at": "now",
            }
        )

    descriptor = broker_runtime._validate_public_descriptor(
        {
            "schema_version": 1,
            "audience": "codex-restricted-windows",
            "pid": 123,
            "port": 7810,
            "protected_token": "p" * 64,
            "started_at": "now",
        }
    )
    assert "token" not in descriptor
    assert json.loads(json.dumps(descriptor))["protected_token"] == "p" * 64


@pytest.mark.parametrize(
    "path",
    [
        "/api/config",
        "/api/hiring/approve",
        "/api/maintenance/trim",
        "/api/roster/action",
        "/api/workforce/action",
    ],
)
def test_broker_token_cannot_call_destructive_endpoints(path: str) -> None:
    """SEC-02: the restricted broker token's path allowlist is the sole guard
    preventing a restricted reader from invoking destructive/administrative
    endpoints. Pin each genuinely-destructive POST route as broker-denied so a
    future endpoint cannot accidentally be exposed to the broker scope."""
    assert dashboard_runtime.dashboard_broker_request_allowed(path, "POST") is False
    assert dashboard_runtime.dashboard_broker_request_allowed(path, "GET") is False


@pytest.mark.parametrize(
    "path",
    [
        "/api/agents/toggle",
        "/api/hosts/toggle",
        "/api/route",
        "/api/runtime/toggle",
        "/api/search",
    ],
)
def test_broker_token_allows_intended_control_endpoints(path: str) -> None:
    """SEC-02 companion: document the endpoints the restricted broker token IS
    intentionally allowed to call (operator control + read-only search/route).
    Pinning these prevents an over-restrictive change from silently breaking
    the broker's supported surface."""
    assert dashboard_runtime.dashboard_broker_request_allowed(path, "POST") is True
