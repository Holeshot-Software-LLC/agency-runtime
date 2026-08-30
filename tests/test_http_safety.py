"""Credential redirect boundaries for provider HTTP requests."""

from __future__ import annotations

import io
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agency_runtime.core.config import ProviderEntry
from agency_runtime.core.doctor import _http_check_authed
from agency_runtime.core.http_safety import open_no_redirect
from agency_runtime.core.provider_validation import validate_provider


def test_credentialed_provider_redirect_is_rejected_before_headers_cross_origin() -> None:
    leaked_headers: list[dict[str, str]] = []

    class SinkHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            leaked_headers.append(dict(self.headers.items()))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_args: object) -> None:
            return None

    sink = ThreadingHTTPServer(("127.0.0.1", 0), SinkHandler)
    sink_url = f"http://127.0.0.1:{sink.server_port}/leak"

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(302)
            self.send_header("Location", sink_url)
            self.end_headers()

        def log_message(self, *_args: object) -> None:
            return None

    origin = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    threads = [
        threading.Thread(target=server.serve_forever, daemon=True) for server in (sink, origin)
    ]
    for thread in threads:
        thread.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{origin.server_port}/models",
            headers={"Authorization": "Bearer secret", "x-api-key": "secret"},
        )
        with pytest.raises(urllib.error.HTTPError) as caught:
            open_no_redirect(request, timeout=2)
        caught.value.close()

        result = validate_provider(
            ProviderEntry(
                name="provider",
                type="openai-compatible",
                model="model",
                base_url=f"http://127.0.0.1:{origin.server_port}/v1",
                api_key="secret",
            ),
            timeout=2,
        )
        doctor_ok, _ = _http_check_authed(
            f"http://127.0.0.1:{origin.server_port}/models",
            "secret",
            timeout=2,
        )

        assert caught.value.code == 302
        assert result.usable is False
        assert doctor_ok is False
        assert leaked_headers == []
    finally:
        for server in (origin, sink):
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)


def test_loopback_requests_explicitly_bypass_environment_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[object] = []

    class Opener:
        def open(self, request: urllib.request.Request, *, timeout: float) -> object:
            assert request.full_url == "http://127.0.0.1:11434/api/tags"
            assert timeout == 2
            return object()

    def build_opener(*handlers: object) -> Opener:
        captured.extend(handlers)
        return Opener()

    monkeypatch.setattr(urllib.request, "build_opener", build_opener)

    open_no_redirect(
        urllib.request.Request("http://127.0.0.1:11434/api/tags"),
        timeout=2,
    )

    proxy_handlers = [
        handler for handler in captured if isinstance(handler, urllib.request.ProxyHandler)
    ]
    assert len(proxy_handlers) == 1
    assert proxy_handlers[0].proxies == {}


def test_http_errors_are_closed_before_they_are_reraised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = io.BytesIO(b"rejected")
    error = urllib.error.HTTPError(
        "https://provider.invalid/v1/models",
        401,
        "Unauthorized",
        None,
        body,
    )

    class RejectingOpener:
        def open(self, *_args: object, **_kwargs: object) -> object:
            raise error

    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: RejectingOpener())

    with pytest.raises(urllib.error.HTTPError) as caught:
        open_no_redirect(
            urllib.request.Request("https://provider.invalid/v1/models"),
            timeout=2,
        )

    assert caught.value is error
    assert body.closed is True


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True])
def test_http_helper_rejects_unbounded_timeouts(timeout: object) -> None:
    with pytest.raises(ValueError, match="timeout"):
        open_no_redirect(
            urllib.request.Request("https://provider.invalid/v1/models"),
            timeout=timeout,  # type: ignore[arg-type]
        )


def test_http_helper_rejects_non_http_schemes() -> None:
    with pytest.raises(ValueError, match=r"HTTP\(S\)"):
        open_no_redirect(
            urllib.request.Request("file:///tmp/provider"),
            timeout=2,
        )
