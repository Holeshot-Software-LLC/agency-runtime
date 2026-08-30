"""Regression tests for quiet public HTTP client-disconnect handling."""

from __future__ import annotations

import errno
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agency_runtime.server import http as http_module


def _raise(exc: BaseException) -> None:
    raise exc


def _handler(path: str) -> http_module.AgencyHTTPHandler:
    handler = object.__new__(http_module.AgencyHTTPHandler)
    handler.path = path
    handler.close_connection = False
    handler.server = SimpleNamespace(store=Mock())
    handler._validate_request_boundary = lambda **_kwargs: True
    handler._read_json_body = lambda: {}
    handler._json_error = Mock()
    return handler


def _enable_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agency_runtime.core.runtime_control.read_enforcement_runtime_control",
        lambda: ({"enabled": True}, None),
    )
    monkeypatch.setattr(
        "agency_runtime.core.config_binding.assert_store_config_binding",
        lambda _store: None,
    )


@pytest.mark.parametrize(
    ("method", "path", "handler_name", "exc"),
    [
        ("GET", "/status", "_handle_status", ConnectionAbortedError("gone")),
        ("POST", "/search", "_handle_search", BrokenPipeError("gone")),
    ],
    ids=["get", "post"],
)
def test_primary_response_disconnect_is_quiet_and_does_not_attempt_500(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    handler_name: str,
    exc: OSError,
) -> None:
    handler = _handler(path)
    primary_response = Mock(side_effect=exc)
    log_failure = Mock()
    handler._json_ok = primary_response
    if method == "GET":
        setattr(handler, handler_name, lambda **_kwargs: handler._json_ok({"status": "ok"}))
    else:
        setattr(handler, handler_name, lambda _body: handler._json_ok({"status": "ok"}))
    monkeypatch.setattr(http_module, "_log_unhandled_request_error", log_failure)
    _enable_runtime(monkeypatch)

    getattr(handler, f"_dispatch_{method}")(path, path.removeprefix("/"))

    assert handler.close_connection is True
    primary_response.assert_called_once_with({"status": "ok"})
    log_failure.assert_not_called()
    handler._json_error.assert_not_called()


@pytest.mark.parametrize(
    ("method", "path", "handler_name"),
    [
        ("GET", "/status", "_handle_status"),
        ("POST", "/search", "_handle_search"),
    ],
    ids=["get", "post"],
)
def test_genuine_request_failure_logs_once_and_attempts_one_500(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    handler_name: str,
) -> None:
    handler = _handler(path)
    failure = TypeError("server defect")
    log_failure = Mock()
    if method == "GET":
        setattr(handler, handler_name, lambda **_kwargs: _raise(failure))
    else:
        setattr(handler, handler_name, lambda _body: _raise(failure))
    monkeypatch.setattr(http_module, "_log_unhandled_request_error", log_failure)
    _enable_runtime(monkeypatch)

    operation = path.removeprefix("/")
    getattr(handler, f"_dispatch_{method}")(path, operation)

    log_failure.assert_called_once_with(method, operation, failure)
    handler._json_error.assert_called_once_with(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "internal server error",
    )
    assert handler.close_connection is False


@pytest.mark.parametrize(
    ("request_method", "path", "handler_name"),
    [
        ("do_GET", "/status", "_handle_status"),
        ("do_POST", "/search", "_handle_search"),
    ],
    ids=["get", "post"],
)
def test_disconnect_during_defensive_500_stops_at_outer_request_boundary(
    monkeypatch: pytest.MonkeyPatch,
    request_method: str,
    path: str,
    handler_name: str,
) -> None:
    handler = _handler(path)
    failure = TypeError("server defect")
    log_failure = Mock()
    error_response = Mock(side_effect=ConnectionResetError("client left before 500"))
    observations: list[object] = []
    handler._json_error = error_response
    if request_method == "do_GET":
        setattr(handler, handler_name, lambda **_kwargs: _raise(failure))
    else:
        setattr(handler, handler_name, lambda _body: _raise(failure))
    monkeypatch.setattr(http_module, "_log_unhandled_request_error", log_failure)
    monkeypatch.setattr(
        "agency_runtime.core.observability.emit_observation",
        observations.append,
    )
    monkeypatch.setattr(
        BaseHTTPRequestHandler,
        "handle_one_request",
        lambda self: getattr(self, request_method)(),
    )
    _enable_runtime(monkeypatch)

    handler.handle_one_request()

    assert handler.close_connection is True
    log_failure.assert_called_once()
    error_response.assert_called_once_with(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "internal server error",
    )
    assert len(observations) == 1
    observation = observations[0]
    assert (
        observation.surface,
        observation.operation,
        observation.outcome,
        observation.reason_code,
    ) == (
        "http",
        http_module._observation_operation(request_method[3:], path),
        "degraded",
        "client_disconnected",
    )


def test_outer_request_boundary_propagates_unrelated_os_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = _handler("/status")
    exc = OSError("filesystem failure")
    exc.errno = errno.EIO
    monkeypatch.setattr(BaseHTTPRequestHandler, "handle_one_request", lambda _self: _raise(exc))

    with pytest.raises(OSError, match="filesystem failure"):
        handler.handle_one_request()

    assert handler.close_connection is False
