"""Credential-safe urllib helpers shared by provider request paths."""

from __future__ import annotations

import urllib.request
from typing import Any


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


def open_no_redirect(
    request: urllib.request.Request,
    *,
    timeout: float,
) -> Any:
    """Open one HTTP request while refusing every redirect response."""

    opener = urllib.request.build_opener(_NoRedirectHandler())
    return opener.open(request, timeout=timeout)


__all__ = ["open_no_redirect"]
