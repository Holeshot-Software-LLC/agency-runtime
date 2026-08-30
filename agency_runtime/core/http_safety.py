"""Credential-safe urllib helpers shared by provider request paths."""

from __future__ import annotations

import ipaddress
import math
import urllib.error
import urllib.request
from contextlib import suppress
from numbers import Real
from typing import Any
from urllib.parse import urlsplit


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects before urllib can copy credentials to another origin."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _is_loopback_destination(url: str) -> bool:
    """Return whether *url* targets a literal loopback address or localhost."""

    try:
        host = (urlsplit(url).hostname or "").rstrip(".").casefold()
        if host == "localhost":
            return True
        return ipaddress.ip_address(host).is_loopback
    except (TypeError, ValueError):
        return False


def open_no_redirect(
    request: urllib.request.Request,
    *,
    timeout: float,
) -> Any:
    """Open one bounded HTTP(S) request while refusing every redirect response.

    Loopback calls bypass environment-configured proxies. Otherwise a hostile or
    accidentally broad ``HTTP_PROXY`` setting could move a request that was
    explicitly trusted as local -- including its credentials -- off-machine.
    """

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, Real)
        or not math.isfinite(float(timeout))
        or float(timeout) <= 0
    ):
        raise ValueError("HTTP timeout must be a positive finite number")
    url = request.full_url
    if urlsplit(url).scheme.casefold() not in {"http", "https"}:
        raise ValueError("only HTTP(S) requests are supported")
    handlers: list[Any] = []
    if _is_loopback_destination(url):
        handlers.append(urllib.request.ProxyHandler({}))
    handlers.append(_NoRedirectHandler())
    opener = urllib.request.build_opener(*handlers)
    try:
        return opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        # HTTPError is both an exception and the response object. Callers treat
        # every HTTP error as a failed probe, so release its socket-backed body
        # before propagating the status-bearing exception.
        with suppress(OSError, ValueError):
            exc.close()
        raise


__all__ = ["open_no_redirect"]
