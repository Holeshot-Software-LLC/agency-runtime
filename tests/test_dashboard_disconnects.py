"""Regression tests for quiet dashboard client-disconnect handling."""

from __future__ import annotations

import errno
from http import HTTPStatus
from unittest.mock import Mock

import pytest

from agency_runtime.server import dashboard as dashboard_module
from agency_runtime.server.http import AgencyHTTPHandler
from agency_runtime.server.http_transport import is_expected_client_disconnect


def _raise(exc: BaseException) -> None:
    raise exc


def _handler(path: str) -> dashboard_module.DashboardHTTPHandler:
    handler = object.__new__(dashboard_module.DashboardHTTPHandler)
    handler.path = path
    handler.close_connection = False
    handler._authorise_api_request = lambda **_kwargs: True
    handler._read_json_body = lambda: {}
    handler._json_error = Mock()
    return handler


@pytest.mark.parametrize(
    "exc",
    [
        BrokenPipeError("client closed"),
        ConnectionAbortedError("client aborted"),
        ConnectionResetError("client reset"),
    ],
    ids=["broken-pipe", "connection-aborted", "connection-reset"],
)
def test_expected_client_disconnect_recognizes_builtin_exceptions(exc: OSError) -> None:
    assert is_expected_client_disconnect(exc) is True


@pytest.mark.parametrize(
    "error_name",
    ["ECONNABORTED", "ECONNRESET", "EPIPE", "ESHUTDOWN", "ENOTCONN"],
)
def test_expected_client_disconnect_recognizes_platform_errno(error_name: str) -> None:
    error_number = getattr(errno, error_name, None)
    if error_number is None:
        pytest.skip(f"{error_name} is unavailable on this platform")
    exc = OSError("platform disconnect")
    exc.errno = error_number

    assert is_expected_client_disconnect(exc) is True


@pytest.mark.parametrize("winerror", [10053, 10054, 10058])
def test_expected_client_disconnect_recognizes_windows_socket_codes(winerror: int) -> None:
    exc = OSError("Windows socket disconnect")
    exc.winerror = winerror

    assert is_expected_client_disconnect(exc) is True


def test_expected_client_disconnect_rejects_unrelated_failures() -> None:
    exc = OSError("permission denied")
    exc.errno = errno.EACCES
    exc.winerror = 5

    assert is_expected_client_disconnect(RuntimeError("bug")) is False
    assert is_expected_client_disconnect(exc) is False


@pytest.mark.parametrize(
    ("request_method", "path", "handler_name", "exc"),
    [
        ("do_GET", "/api/live", "_handle_live", ConnectionAbortedError("gone")),
        ("do_POST", "/api/route", "_handle_route_lab", BrokenPipeError("gone")),
    ],
    ids=["get", "post"],
)
def test_request_disconnect_is_quiet_and_does_not_attempt_error_response(
    monkeypatch: pytest.MonkeyPatch,
    request_method: str,
    path: str,
    handler_name: str,
    exc: OSError,
) -> None:
    handler = _handler(path)
    log_exception = Mock()
    monkeypatch.setattr(dashboard_module.logger, "exception", log_exception)
    setattr(handler, handler_name, lambda *_args: _raise(exc))

    getattr(handler, request_method)()

    assert handler.close_connection is True
    log_exception.assert_not_called()
    handler._json_error.assert_not_called()


@pytest.mark.parametrize(
    ("request_method", "path", "handler_name"),
    [
        ("do_GET", "/api/live", "_handle_live"),
        ("do_POST", "/api/route", "_handle_route_lab"),
    ],
    ids=["get", "post"],
)
def test_genuine_request_failure_still_logs_and_returns_500(
    monkeypatch: pytest.MonkeyPatch,
    request_method: str,
    path: str,
    handler_name: str,
) -> None:
    handler = _handler(path)
    log_exception = Mock()
    monkeypatch.setattr(dashboard_module.logger, "exception", log_exception)
    setattr(handler, handler_name, lambda *_args: _raise(TypeError("server defect")))

    getattr(handler, request_method)()

    operation = dashboard_module._dashboard_observation_operation(request_method[3:], path)
    log_exception.assert_called_once_with(
        f"dashboard {request_method[3:]} failed for %s (%s)",
        operation,
        "TypeError",
    )
    handler._json_error.assert_called_once_with(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "internal server error",
    )
    assert handler.close_connection is False


def test_outer_request_boundary_quiets_disconnect_during_500_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = _handler("/api/live")
    log_exception = Mock()
    error_response = Mock(side_effect=ConnectionResetError("client left before 500"))
    observations: list[object] = []
    handler._handle_live = lambda: _raise(TypeError("server defect"))
    handler._json_error = error_response
    monkeypatch.setattr(dashboard_module.logger, "exception", log_exception)
    monkeypatch.setattr(
        "agency_runtime.core.observability.emit_observation",
        observations.append,
    )
    monkeypatch.setattr(
        AgencyHTTPHandler,
        "handle_one_request",
        lambda self: dashboard_module.DashboardHTTPHandler.do_GET(self),
    )

    handler.handle_one_request()

    assert handler.close_connection is True
    log_exception.assert_called_once()
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
    ) == ("dashboard", "live", "degraded", "client_disconnected")


def test_outer_request_boundary_propagates_unrelated_os_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = _handler("/api/live")
    exc = OSError("filesystem failure")
    exc.errno = errno.EIO
    monkeypatch.setattr(AgencyHTTPHandler, "handle_one_request", lambda _self: _raise(exc))

    with pytest.raises(OSError, match="filesystem failure"):
        handler.handle_one_request()

    assert handler.close_connection is False


def test_outer_request_boundary_preserves_normal_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = _handler("/api/live")
    completed: list[bool] = []
    monkeypatch.setattr(
        AgencyHTTPHandler,
        "handle_one_request",
        lambda _self: completed.append(True),
    )

    handler.handle_one_request()

    assert completed == [True]
    assert handler.close_connection is False
