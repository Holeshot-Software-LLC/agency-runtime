"""Credential redirect boundaries for provider HTTP requests."""

from __future__ import annotations

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
        threading.Thread(target=server.serve_forever, daemon=True)
        for server in (sink, origin)
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
